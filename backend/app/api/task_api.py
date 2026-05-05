import hashlib
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.task_schema import (
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskPartyCreate,
    TaskPartyUpdate,
)
from app.services import task_service
from app.services.task_result_service import TaskResultService
from app.schemas.audit_log_schema import AuditLogCreate
from app.services.audit_log_service import AuditLogService
from app.models.chain_record import ChainRecord
from app.models.task_result import TaskResult

router = APIRouter(
    prefix="/api/tasks",
    tags=["联合统计任务管理"],
)


def write_task_audit_log(
    db: Session,
    request: Request,
    current_user,
    operation_type: str,
    object_type: str,
    object_id: str | None = None,
    task_id: int | None = None,
    operation_desc: str | None = None,
    request_json: dict | None = None,
    result_json: dict | None = None,
):
    """
    写入任务相关审计日志。
    """
    ip_address = None
    if request.client:
        ip_address = request.client.host

    operator_user_id = getattr(current_user, "id", None)
    agency_id = getattr(current_user, "agency_id", None)

    AuditLogService.create_log(
        db=db,
        log_req=AuditLogCreate(
            task_id=task_id,
            agency_id=agency_id,
            operator_user_id=operator_user_id,
            operation_type=operation_type,
            object_type=object_type,
            object_id=object_id,
            operation_desc=operation_desc,
            request_json=request_json,
            result_json=result_json,
            ip_address=ip_address,
        ),
    )


def _safe_dict(value: Any) -> dict:
    """
    兼容 result_json / metrics_json 可能为空或不是 dict 的情况。
    """
    if isinstance(value, dict):
        return value
    return {}

def _safe_json_dict(value: Any) -> dict:
    """
    兼容 JSON 字段可能是 dict / str / None 的情况。
    """
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            data = json.loads(value)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    return {}


def _calc_sha256(data: dict) -> str:
    """
    对摘要内容计算 SHA256。
    """
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _build_mock_tx_hash(task_id: int, result_id: int, content_hash: str, now: datetime) -> str:
    """
    生成 Mock 交易哈希。
    后续接入真实 FISCO BCOS 时，替换为真实 tx_hash。
    """
    raw = f"mock_fisco_bcos|task_result|{task_id}|{result_id}|{content_hash}|{now.isoformat()}"
    return "0x" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _chain_record_to_dict(record: ChainRecord) -> dict:
    """
    chain_record ORM 转 dict。
    """
    return {
        "id": record.id,
        "biz_type": record.biz_type,
        "biz_id": record.biz_id,
        "content_hash": record.content_hash,
        "chain_type": record.chain_type,
        "tx_hash": record.tx_hash,
        "block_number": record.block_number,
        "contract_address": record.contract_address,
        "status": record.status,
        "error_message": record.error_message,
        "created_at": record.created_at,
    }


def _build_task_result_anchor_payload(task, task_result: TaskResult) -> dict:
    """
    组装任务结果存证摘要。

    注意：
    只存摘要，不存原始数据、不存完整训练轮次、不存模型参数。
    """
    params_json = _safe_json_dict(getattr(task, "params_json", None))
    result_json = _safe_json_dict(task_result.result_json)
    metrics_json = _safe_json_dict(task_result.metrics_json)
    summary = _safe_json_dict(result_json.get("summary"))

    task_type = (
        params_json.get("task_type")
        or result_json.get("task_type")
        or "statistic"
    )

    base_payload = {
        "biz_type": "task_result",
        "task_id": task.id,
        "task_code": task.task_code,
        "task_name": task.task_name,
        "task_type": task_type,
        "task_status": task.status,
        "result_id": task_result.id,
        "result_status": task_result.status,
        "result_hash": task_result.result_hash,
    }

    if task_type == "federated_learning":
        return {
            **base_payload,
            "scenario_code": result_json.get("scenario_code") or params_json.get("scenario_code"),
            "scenario_name": result_json.get("scenario_name") or params_json.get("scenario_name"),
            "model_type": result_json.get("model_type") or params_json.get("model_type"),
            "framework": result_json.get("framework") or params_json.get("framework"),
            "round_count": summary.get("round_count") or metrics_json.get("round_count"),
            "participant_count": summary.get("participant_count") or metrics_json.get("participant_count"),
            "sample_count": summary.get("sample_count"),
            "final_accuracy": summary.get("final_accuracy") or metrics_json.get("final_accuracy"),
            "final_loss": summary.get("final_loss") or metrics_json.get("final_loss"),
            "final_auc": summary.get("final_auc") or metrics_json.get("final_auc"),
            "privacy_mode": summary.get("privacy_mode"),
            "raw_data_export": summary.get("raw_data_export"),
        }

    return {
        **base_payload,
        "case_count": result_json.get("case_count") or metrics_json.get("case_count"),
        "unique_patient_count": result_json.get("unique_patient_count") or metrics_json.get("unique_patient_count"),
        "positive_count": result_json.get("positive_count") or metrics_json.get("positive_count"),
        "positive_rate": result_json.get("positive_rate") or metrics_json.get("positive_rate"),
    }


def _get_task_type_from_run_data(data: dict) -> str:
    """
    从任务执行返回数据中识别任务类型。
    """
    task = _safe_dict(data.get("task"))
    params_json = _safe_dict(task.get("params_json"))

    return params_json.get("task_type") or "statistic"


def _build_task_run_audit_desc(data: dict) -> str:
    """
    生成 TASK_RUN 审计描述。
    """
    task_type = _get_task_type_from_run_data(data)

    if task_type == "federated_learning":
        return "Mock 执行联邦学习训练任务并生成训练结果"

    return "Mock 执行联合统计任务并生成统计结果"


def _build_task_run_audit_result(data: dict) -> dict:
    """
    生成 TASK_RUN 审计结果摘要。

    注意：
    这里只记录审计摘要，不把完整训练轮次、完整统计结果重复塞进审计日志。
    完整结果仍然以 task_result 为准。
    """
    task = _safe_dict(data.get("task"))
    result = _safe_dict(data.get("result"))

    params_json = _safe_dict(task.get("params_json"))
    result_json = _safe_dict(result.get("result_json"))
    metrics_json = _safe_dict(result.get("metrics_json"))
    summary = _safe_dict(result_json.get("summary"))

    task_type = params_json.get("task_type") or result_json.get("task_type") or "statistic"

    base_payload = {
        "task_id": task.get("id"),
        "task_code": task.get("task_code"),
        "task_name": task.get("task_name"),
        "task_type": task_type,
        "task_status": task.get("status"),
        "result_id": result.get("id"),
        "result_status": result.get("status"),
        "result_hash": result.get("result_hash"),
        "message": data.get("message"),
    }

    if task_type == "federated_learning":
        return {
            **base_payload,
            "scenario_code": result_json.get("scenario_code") or params_json.get("scenario_code"),
            "scenario_name": result_json.get("scenario_name") or params_json.get("scenario_name"),
            "model_type": result_json.get("model_type") or params_json.get("model_type"),
            "framework": result_json.get("framework") or params_json.get("framework"),
            "round_count": summary.get("round_count") or metrics_json.get("round_count"),
            "participant_count": summary.get("participant_count") or metrics_json.get("participant_count"),
            "sample_count": summary.get("sample_count"),
            "final_accuracy": summary.get("final_accuracy") or metrics_json.get("final_accuracy"),
            "final_loss": summary.get("final_loss") or metrics_json.get("final_loss"),
            "final_auc": summary.get("final_auc") or metrics_json.get("final_auc"),
            "privacy_mode": summary.get("privacy_mode"),
            "raw_data_export": summary.get("raw_data_export"),
        }

    return {
        **base_payload,
        "case_count": result_json.get("case_count") or metrics_json.get("case_count"),
        "unique_patient_count": result_json.get("unique_patient_count") or metrics_json.get("unique_patient_count"),
        "positive_count": result_json.get("positive_count") or metrics_json.get("positive_count"),
        "positive_rate": result_json.get("positive_rate") or metrics_json.get("positive_rate"),
    }


@router.get("")
def list_tasks(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    status: str | None = Query(default=None, description="任务状态"),
    keyword: str | None = Query(default=None, description="任务名称关键词"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.list_tasks(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
    )
    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.post("")
def create_task(
    task_create: TaskCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    创建任务。

    说明：
    1. creator_user_id 不由前端传入；
    2. 后端从当前登录用户 current_user 中自动写入；
    3. creator_agency_id 如果前端已经选择，则保留前端选择；
       如果前端没传，则尝试使用当前用户所属机构。
    """
    creator_user_id = getattr(current_user, "id", None)
    creator_agency_id = getattr(current_user, "agency_id", None)

    task_create_with_user = task_create.model_copy(
        update={
            "creator_user_id": creator_user_id,
            "creator_agency_id": task_create.creator_agency_id or creator_agency_id,
        }
    )

    data = task_service.create_task(
        db=db,
        task_create=task_create,
        creator_user_id=creator_user_id,
        creator_agency_id=creator_agency_id,
    )

    task_params = task_create_with_user.params_json or {}
    task_type = task_params.get("task_type") or "statistic"

    operation_desc = (
        "创建联邦学习任务"
        if task_type == "federated_learning"
        else "创建联合统计任务"
    )

    request_json = task_create_with_user.model_dump()
    request_json["task_type"] = task_type

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_CREATE",
        object_type="task",
        object_id=str(data.get("id")),
        task_id=data.get("id"),
        operation_desc=operation_desc,
        request_json=request_json,
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.get("/{task_id}")
def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.get_task_detail(
        db=db,
        task_id=task_id,
    )
    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.put("/{task_id}")
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.update_task(
        db=db,
        task_id=task_id,
        task_update=task_update,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_UPDATE",
        object_type="task",
        object_id=str(task_id),
        task_id=task_id,
        operation_desc="修改联合统计任务",
        request_json=task_update.model_dump(exclude_unset=True),
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.put("/{task_id}/status")
def update_task_status(
    task_id: int,
    status_update: TaskStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.update_task_status(
        db=db,
        task_id=task_id,
        status_update=status_update,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_STATUS_UPDATE",
        object_type="task",
        object_id=str(task_id),
        task_id=task_id,
        operation_desc="更新联合统计任务状态",
        request_json=status_update.model_dump(),
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.get("/{task_id}/parties")
def list_task_parties(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.list_task_parties(db=db, task_id=task_id)
    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.post("/{task_id}/parties")
def create_task_party(
    task_id: int,
    party_create: TaskPartyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.create_task_party(
        db=db,
        task_id=task_id,
        party_create=party_create,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_PARTY_CREATE",
        object_type="task_party",
        object_id=str(data.get("id")),
        task_id=task_id,
        operation_desc="新增任务参与方",
        request_json=party_create.model_dump(),
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.put("/{task_id}/parties/{party_id}")
def update_task_party(
    task_id: int,
    party_id: int,
    party_update: TaskPartyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.update_task_party(
        db=db,
        task_id=task_id,
        party_id=party_id,
        party_update=party_update,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_PARTY_UPDATE",
        object_type="task_party",
        object_id=str(party_id),
        task_id=task_id,
        operation_desc="修改任务参与方",
        request_json=party_update.model_dump(exclude_unset=True),
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.delete("/{task_id}/parties/{party_id}")
def delete_task_party(
    task_id: int,
    party_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.delete_task_party(
        db=db,
        task_id=task_id,
        party_id=party_id,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_PARTY_DELETE",
        object_type="task_party",
        object_id=str(party_id),
        task_id=task_id,
        operation_desc="删除任务参与方",
        request_json={
            "task_id": task_id,
            "party_id": party_id,
        },
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.post("/{task_id}/chain-anchor")
def mock_anchor_task_result(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Mock 任务结果存证。

    当前阶段不接入真实 FISCO BCOS，只完成：
    1. 结果摘要组装；
    2. content_hash 生成；
    3. mock tx_hash / block_number 生成；
    4. chain_record 写入；
    5. 审计日志写入。

    后续第十八阶段接入真实 FISCO BCOS 时，
    替换 tx_hash / block_number / contract_address 的生成逻辑即可。
    """
    task = task_service.get_task_or_404(db=db, task_id=task_id)

    if task.status != "success":
        raise HTTPException(
            status_code=400,
            detail="任务尚未成功完成，不能进行结果存证",
        )

    task_result = (
        db.query(TaskResult)
        .filter(TaskResult.task_id == task_id)
        .first()
    )

    if not task_result:
        raise HTTPException(
            status_code=404,
            detail="任务结果不存在，请先执行任务",
        )

    if task_result.status != "success":
        raise HTTPException(
            status_code=400,
            detail="任务结果状态不是 success，不能进行结果存证",
        )

    anchor_payload = _build_task_result_anchor_payload(
        task=task,
        task_result=task_result,
    )

    content_hash = task_result.result_hash or _calc_sha256(anchor_payload)

    # 避免同一个结果重复存证
    exists_record = (
        db.query(ChainRecord)
        .filter(
            ChainRecord.biz_type == "task_result",
            ChainRecord.biz_id == str(task_result.id),
            ChainRecord.content_hash == content_hash,
            ChainRecord.status == "success",
        )
        .first()
    )

    if exists_record:
        data = {
            "anchored": True,
            "duplicated": True,
            "message": "当前任务结果已完成存证，无需重复存证",
            "anchor_payload": anchor_payload,
            "chain_record": _chain_record_to_dict(exists_record),
        }

        return {
            "code": 0,
            "message": "success",
            "data": data,
        }

    now = datetime.now()
    tx_hash = _build_mock_tx_hash(
        task_id=task.id,
        result_id=task_result.id,
        content_hash=content_hash,
        now=now,
    )

    chain_record = ChainRecord(
        biz_type="task_result",
        biz_id=str(task_result.id),
        content_hash=content_hash,
        chain_type="mock_fisco_bcos",
        tx_hash=tx_hash,
        block_number=int(now.timestamp()),
        contract_address="0xMockTaskResultAnchorContract",
        status="success",
        error_message=None,
    )

    db.add(chain_record)
    db.commit()
    db.refresh(chain_record)

    chain_record_data = _chain_record_to_dict(chain_record)

    audit_result_json = {
        "message": "Mock 任务结果存证成功",
        "task_id": task.id,
        "task_code": task.task_code,
        "task_name": task.task_name,
        "result_id": task_result.id,
        "result_hash": task_result.result_hash,
        "content_hash": content_hash,
        "chain_record_id": chain_record.id,
        "chain_type": chain_record.chain_type,
        "tx_hash": chain_record.tx_hash,
        "block_number": chain_record.block_number,
        "contract_address": chain_record.contract_address,
        "status": chain_record.status,
    }

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_RESULT_CHAIN_ANCHOR",
        object_type="chain_record",
        object_id=str(chain_record.id),
        task_id=task.id,
        operation_desc="Mock 任务结果存证",
        request_json={
            "task_id": task.id,
            "result_id": task_result.id,
            "biz_type": "task_result",
            "content_hash": content_hash,
        },
        result_json=audit_result_json,
    )

    data = {
        "anchored": True,
        "duplicated": False,
        "message": "Mock 任务结果存证成功",
        "anchor_payload": anchor_payload,
        "chain_record": chain_record_data,
    }

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.post("/{task_id}/run")
def mock_run_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Mock 执行任务。

    说明：
    1. 联合统计任务：task_service 负责执行状态流转，TaskResultService 负责生成统计结果；
    2. 联邦学习任务：task_service 内部直接生成 Mock 联邦训练结果；
    3. 这里根据 data 中是否已有 result 判断是否还需要生成联合统计结果。
    """
    data = task_service.mock_run_task(
        db=db,
        task_id=task_id,
    )

    # 如果 task_service 已经生成 result，说明是联邦学习任务，不能再生成联合统计结果
    if not data.get("result"):
        result = TaskResultService.create_or_update_mock_result(
            db=db,
            task_id=task_id,
        )

        data["result"] = TaskResultService.build_result_info(result)
        data["message"] = "Mock 联合统计任务执行成功，已生成统计结果"

    operation_desc = _build_task_run_audit_desc(data)
    audit_result_json = _build_task_run_audit_result(data)

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_RUN",
        object_type="task",
        object_id=str(task_id),
        task_id=task_id,
        operation_desc=operation_desc,
        request_json={
            "task_id": task_id,
            "task_type": audit_result_json.get("task_type"),
        },
        result_json=audit_result_json,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }