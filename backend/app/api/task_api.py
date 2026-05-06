import hashlib
import json
from datetime import datetime
from typing import Any
from urllib import error as url_error
from urllib import request as url_request

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.schemas.task_schema import (
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskPartyCreate,
    TaskPartyUpdate,
)
from app.services import task_service
from app.services.secretflow_stat_service import SecretFlowStatService
from app.services.secretflow_fl_service import SecretFlowFLService
from app.services.task_result_service import TaskResultService
from app.schemas.audit_log_schema import AuditLogCreate
from app.services.audit_log_service import AuditLogService
from app.models.chain_record import ChainRecord
from app.models.task_result import TaskResult
from app.models.task_party import TaskParty

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




def _get_stat_date_str(value, default_value: str) -> str:
    """
    将 task.stat_start_time / stat_end_time 转成 YYYY-MM-DD。
    """
    if value is None:
        return default_value

    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")

    text = str(value)
    return text[:10] if len(text) >= 10 else default_value


def _build_secretflow_stat_request(task) -> dict:
    """
    根据任务参数组装 SecretFlow 联合统计请求。

    说明：
    - 第十九阶段 MVP 默认跑 Alice/Bob 两方流感样病例统计；
    - CSV 路径优先从 params_json.secretflow 读取，未配置则使用 settings 默认值；
    - 时间范围优先使用任务 stat_start_time / stat_end_time。
    """
    params_json = _safe_json_dict(getattr(task, "params_json", None))
    secretflow_params = _safe_json_dict(params_json.get("secretflow"))

    start_date = (
        params_json.get("start_date")
        or secretflow_params.get("start_date")
        or _get_stat_date_str(task.stat_start_time, settings.SECRETFLOW_DEFAULT_START_DATE)
    )
    end_date = (
        params_json.get("end_date")
        or secretflow_params.get("end_date")
        or _get_stat_date_str(task.stat_end_time, settings.SECRETFLOW_DEFAULT_END_DATE)
    )
    syndrome_type = (
        params_json.get("syndrome_type")
        or secretflow_params.get("syndrome_type")
        or settings.SECRETFLOW_DEFAULT_SYNDROME_TYPE
    )

    return {
        "task_id": task.task_code or f"task_{task.id}",
        "start_date": start_date,
        "end_date": end_date,
        "syndrome_type": syndrome_type,
        "alice_csv": secretflow_params.get("alice_csv") or settings.SECRETFLOW_ALICE_CSV,
        "bob_csv": secretflow_params.get("bob_csv") or settings.SECRETFLOW_BOB_CSV,
    }




def _build_secretflow_fl_request(task) -> dict:
    """
    根据任务参数组装 SecretFlow 联邦学习训练请求。

    说明：
    - 第一版优先接入 Alice 端 18181 横向联邦学习训练服务；
    - 参数优先从 params_json.secretflow_fl / params_json.train_config 读取；
    - 未配置时使用 settings 中的默认训练参数。
    """
    params_json = _safe_json_dict(getattr(task, "params_json", None))
    secretflow_fl_params = _safe_json_dict(params_json.get("secretflow_fl"))
    train_config = _safe_json_dict(params_json.get("train_config"))

    train_mode = (
        params_json.get("train_mode")
        or params_json.get("partition_type")
        or secretflow_fl_params.get("train_mode")
        or secretflow_fl_params.get("partition_type")
        or "horizontal"
    )

    epochs = (
        train_config.get("epochs")
        or secretflow_fl_params.get("epochs")
        or getattr(settings, "SECRETFLOW_FL_EPOCHS", 5)
    )
    batch_size = (
        train_config.get("batch_size")
        or secretflow_fl_params.get("batch_size")
        or getattr(settings, "SECRETFLOW_FL_BATCH_SIZE", 32)
    )
    learning_rate = (
        train_config.get("learning_rate")
        or secretflow_fl_params.get("learning_rate")
        or getattr(settings, "SECRETFLOW_FL_LEARNING_RATE", 0.001)
    )

    return {
        "task_id": task.task_code or f"task_{task.id}",
        "train_mode": train_mode,
        "alice_csv": (
            secretflow_fl_params.get("alice_csv")
            or params_json.get("alice_csv")
            or getattr(settings, "SECRETFLOW_FL_ALICE_CSV", "/data/alice_flu_fl_train.csv")
        ),
        "bob_csv": (
            secretflow_fl_params.get("bob_csv")
            or params_json.get("bob_csv")
            or getattr(settings, "SECRETFLOW_FL_BOB_CSV", "/data/bob_flu_fl_train.csv")
        ),
        "epochs": int(epochs),
        "batch_size": int(batch_size),
        "learning_rate": float(learning_rate),
    }


def _task_result_to_dict(task_result: TaskResult) -> dict:
    return {
        "id": task_result.id,
        "task_id": task_result.task_id,
        "result_json": task_result.result_json,
        "metrics_json": task_result.metrics_json,
        "result_hash": task_result.result_hash,
        "status": task_result.status,
        "error_message": task_result.error_message,
        "created_at": task_result.created_at,
        "updated_at": task_result.updated_at,
    }


def _create_or_update_secretflow_stat_result(
    db: Session,
    task,
    sf_payload: dict,
) -> TaskResult:
    """
    将 SecretFlow 联合统计结果写入 task_result。

    注意：
    - result_hash 使用 Alice SecretFlow 服务返回的稳定摘要；
    - 不在这里上链，上链继续复用 /api/tasks/{task_id}/chain-anchor。
    """
    result_json = _safe_json_dict(sf_payload.get("result"))

    metrics_json = {
        "case_count": result_json.get("case_count"),
        "sampled_count": result_json.get("sampled_count"),
        "positive_count": result_json.get("positive_count"),
        "positive_rate": result_json.get("positive_rate"),
        "unique_patient_count": result_json.get("unique_patient_count"),
        "unique_patient_count_mode": result_json.get("unique_patient_count_mode"),
        "local_dedup_patient_count_sum": result_json.get("local_dedup_patient_count_sum"),
        "framework": result_json.get("framework"),
        "scenario_code": result_json.get("scenario_code"),
        "scenario_name": result_json.get("scenario_name"),
    }

    result_hash = sf_payload.get("result_hash") or _calc_sha256(result_json)

    task_result = (
        db.query(TaskResult)
        .filter(TaskResult.task_id == task.id)
        .first()
    )

    now = datetime.now()

    if task_result:
        task_result.result_json = result_json
        task_result.metrics_json = metrics_json
        task_result.result_hash = result_hash
        task_result.status = "success"
        task_result.error_message = None
        task_result.updated_at = now
    else:
        task_result = TaskResult(
            task_id=task.id,
            result_json=result_json,
            metrics_json=metrics_json,
            result_hash=result_hash,
            status="success",
            error_message=None,
        )
        db.add(task_result)

    return task_result




def _create_or_update_secretflow_fl_result(
    db: Session,
    task,
    sf_payload: dict,
) -> TaskResult:
    """
    将 SecretFlow 联邦学习训练结果写入 task_result。

    注意：
    - 这里不写模型参数、不写原始数据；
    - result_hash 优先使用 Alice 端 18181 服务返回的训练结果摘要；
    - 后续上链继续复用 /api/tasks/{task_id}/chain-anchor。
    """
    params_json = _safe_json_dict(getattr(task, "params_json", None))
    result_json = _safe_json_dict(sf_payload.get("result"))

    metrics = _safe_json_dict(result_json.get("metrics"))
    training_params = _safe_json_dict(result_json.get("training_params"))

    participants = result_json.get("participants") or []
    if not isinstance(participants, list):
        participants = []

    summary = _safe_json_dict(result_json.get("summary"))
    summary.update(
        {
            "final_accuracy": summary.get("final_accuracy") or metrics.get("accuracy"),
            "final_auc": summary.get("final_auc") or metrics.get("auc"),
            "final_precision": summary.get("final_precision") or metrics.get("precision"),
            "final_recall": summary.get("final_recall") or metrics.get("recall"),
            "final_f1": summary.get("final_f1") or metrics.get("f1"),
            "round_count": summary.get("round_count") or training_params.get("epochs"),
            "participant_count": summary.get("participant_count") or len(participants),
            "sample_count": summary.get("sample_count") or metrics.get("sample_count"),
            "privacy_mode": summary.get("privacy_mode")
            or result_json.get("aggregator")
            or result_json.get("partition_type"),
            "raw_data_export": False,
        }
    )

    result_json.update(
        {
            "task_type": "federated_learning",
            "task_id": task.task_code or f"task_{task.id}",
            "scenario_code": (
                result_json.get("scenario_code")
                or params_json.get("scenario_code")
                or "flu_federated_learning"
            ),
            "scenario_name": (
                result_json.get("scenario_name")
                or params_json.get("scenario_name")
                or "流感样病例联邦学习训练"
            ),
            "framework": result_json.get("framework") or "secretflow",
            "summary": summary,
        }
    )

    metrics_json = {
        "final_accuracy": summary.get("final_accuracy"),
        "final_auc": summary.get("final_auc"),
        "final_precision": summary.get("final_precision"),
        "final_recall": summary.get("final_recall"),
        "final_f1": summary.get("final_f1"),
        "round_count": summary.get("round_count"),
        "participant_count": summary.get("participant_count"),
        "sample_count": summary.get("sample_count"),
        "privacy_mode": summary.get("privacy_mode"),
        "raw_data_export": summary.get("raw_data_export"),
        "framework": result_json.get("framework"),
        "model_type": result_json.get("model_type"),
        "partition_type": result_json.get("partition_type"),
        "strategy": result_json.get("strategy"),
        "aggregator": result_json.get("aggregator"),
    }

    result_hash = (
        sf_payload.get("result_hash")
        or result_json.get("result_hash")
        or _calc_sha256(result_json)
    )

    task_result = (
        db.query(TaskResult)
        .filter(TaskResult.task_id == task.id)
        .first()
    )

    now = datetime.now()

    if task_result:
        task_result.result_json = result_json
        task_result.metrics_json = metrics_json
        task_result.result_hash = result_hash
        task_result.status = "success"
        task_result.error_message = None
        task_result.updated_at = now
    else:
        task_result = TaskResult(
            task_id=task.id,
            result_json=result_json,
            metrics_json=metrics_json,
            result_hash=result_hash,
            status="success",
            error_message=None,
        )
        db.add(task_result)

    return task_result


def _run_secretflow_federated_learning_task(db: Session, task) -> dict:
    """
    执行 SecretFlow 联邦学习训练任务并写入 task_result。
    """
    parties = (
        db.query(TaskParty)
        .filter(TaskParty.task_id == task.id)
        .order_by(TaskParty.id.asc())
        .all()
    )

    if not parties:
        raise HTTPException(status_code=400, detail="联邦学习任务尚未配置训练节点，不能执行")

    task.status = "running"
    for party in parties:
        party.status = "running"
        party.error_message = None

    db.commit()

    try:
        fl_request = _build_secretflow_fl_request(task)

        sf_payload = SecretFlowFLService.run_flu_fl_train(
            task_id=fl_request["task_id"],
            train_mode=fl_request["train_mode"],
            alice_csv=fl_request["alice_csv"],
            bob_csv=fl_request["bob_csv"],
            epochs=fl_request["epochs"],
            batch_size=fl_request["batch_size"],
            learning_rate=fl_request["learning_rate"],
        )

        task_result = _create_or_update_secretflow_fl_result(
            db=db,
            task=task,
            sf_payload=sf_payload,
        )

        task.status = "success"
        for party in parties:
            party.status = "success"
            party.error_message = None

        if hasattr(task, "updated_at"):
            task.updated_at = datetime.now()

        db.commit()
        db.refresh(task)
        db.refresh(task_result)

        return {
            "task": task_service.task_to_dict(task),
            "parties": [task_service.party_to_dict(party) for party in parties],
            "result": _task_result_to_dict(task_result),
            "secretflow_fl_request": fl_request,
            "secretflow_fl_response": {
                "success": sf_payload.get("success"),
                "message": sf_payload.get("message"),
                "task_id": sf_payload.get("task_id"),
                "timestamp": sf_payload.get("timestamp"),
                "train_mode": sf_payload.get("train_mode"),
                "result_hash": sf_payload.get("result_hash"),
            },
            "message": "SecretFlow 联邦学习训练任务执行成功，已生成训练结果",
        }

    except Exception as exc:
        task.status = "failed"
        for party in parties:
            party.status = "failed"
            party.error_message = str(exc)

        if hasattr(task, "updated_at"):
            task.updated_at = datetime.now()

        db.commit()
        raise


def _run_secretflow_statistic_task(db: Session, task) -> dict:
    """
    执行 SecretFlow 联合统计任务并写入 task_result。
    """
    parties = (
        db.query(TaskParty)
        .filter(TaskParty.task_id == task.id)
        .order_by(TaskParty.id.asc())
        .all()
    )

    if not parties:
        raise HTTPException(status_code=400, detail="任务尚未配置参与方，不能执行")

    task.status = "running"
    for party in parties:
        party.status = "running"
        party.error_message = None

    db.commit()

    try:
        sf_request = _build_secretflow_stat_request(task)

        sf_payload = SecretFlowStatService.run_flu_stat(
            task_id=sf_request["task_id"],
            start_date=sf_request["start_date"],
            end_date=sf_request["end_date"],
            syndrome_type=sf_request["syndrome_type"],
            alice_csv=sf_request["alice_csv"],
            bob_csv=sf_request["bob_csv"],
        )

        task_result = _create_or_update_secretflow_stat_result(
            db=db,
            task=task,
            sf_payload=sf_payload,
        )

        task.status = "success"
        for party in parties:
            party.status = "success"
            party.error_message = None

        if hasattr(task, "updated_at"):
            task.updated_at = datetime.now()

        db.commit()
        db.refresh(task)
        db.refresh(task_result)

        return {
            "task": task_service.task_to_dict(task),
            "parties": [task_service.party_to_dict(party) for party in parties],
            "result": _task_result_to_dict(task_result),
            "secretflow_request": sf_request,
            "secretflow_response": {
                "success": sf_payload.get("success"),
                "message": sf_payload.get("message"),
                "task_id": sf_payload.get("task_id"),
                "timestamp": sf_payload.get("timestamp"),
                "result_hash": sf_payload.get("result_hash"),
            },
            "message": "SecretFlow 联合统计任务执行成功，已生成统计结果",
        }

    except Exception as exc:
        task.status = "failed"
        for party in parties:
            party.status = "failed"
            party.error_message = str(exc)

        if hasattr(task, "updated_at"):
            task.updated_at = datetime.now()

        db.commit()
        raise


def _calc_sha256(data: dict) -> str:
    """
    对摘要内容计算 SHA256。
    """
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _call_fisco_anchor_service(anchor_task_id: str, digest: str, timestamp: int) -> dict:
    """
    调用 Alice 节点上的 FISCO BCOS 上链服务。

    当前 FastAPI 运行在 Windows 本地，不直接加载 FISCO BCOS Python SDK，
    只通过 HTTP 调用 Alice 的 fisco_anchor_service。
    """
    base_url = settings.FISCO_ANCHOR_SERVICE_URL.rstrip("/")
    url = f"{base_url}/anchor/result"

    payload = {
        "task_id": anchor_task_id,
        "digest": digest,
        "timestamp": timestamp,
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": settings.FISCO_ANCHOR_API_KEY,
    }

    req = url_request.Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with url_request.urlopen(req, timeout=settings.FISCO_ANCHOR_TIMEOUT_SECONDS) as resp:
            resp_body = resp.read().decode("utf-8")
    except url_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(
            status_code=502,
            detail=f"FISCO 上链服务返回异常: HTTP {exc.code}, {error_body}",
        ) from exc
    except url_error.URLError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"无法连接 FISCO 上链服务: {exc.reason}",
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="调用 FISCO 上链服务超时",
        ) from exc

    try:
        data = json.loads(resp_body)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"FISCO 上链服务返回非 JSON 内容: {resp_body}",
        ) from exc

    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="FISCO 上链服务返回格式错误")

    if not data.get("success"):
        raise HTTPException(
            status_code=502,
            detail=f"FISCO 上链失败: {data}",
        )

    if data.get("verify_result") is False:
        raise HTTPException(
            status_code=502,
            detail=f"FISCO 上链后校验失败: {data}",
        )

    return data


def _extract_chain_tx_hash(anchor_response: dict) -> str | None:
    raw_receipt = _safe_json_dict(anchor_response.get("raw_receipt"))
    return anchor_response.get("tx_hash") or raw_receipt.get("transactionHash")


def _extract_chain_block_number(anchor_response: dict) -> int | None:
    raw_receipt = _safe_json_dict(anchor_response.get("raw_receipt"))
    block_number = anchor_response.get("block_number") or raw_receipt.get("blockNumber")
    if block_number is None:
        return None
    try:
        return int(block_number)
    except Exception:
        return None


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
        return "执行 SecretFlow 联邦学习训练任务并生成训练结果"

    return "执行 SecretFlow 联合统计任务并生成统计结果"


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
def anchor_task_result(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    任务结果真实上链存证。

    当前实现方式：
    1. FastAPI 查询任务和任务结果；
    2. 组装任务结果摘要并计算 content_hash；
    3. 调用 Alice 节点 fisco_anchor_service；
    4. 使用真实返回的 tx_hash / block_number / contract_address 写入 chain_record；
    5. 写入 TASK_RESULT_CHAIN_ANCHOR 审计日志。
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
    anchor_task_id = f"task_result_{task_result.id}"
    anchor_timestamp = int(now.timestamp())

    anchor_response = _call_fisco_anchor_service(
        anchor_task_id=anchor_task_id,
        digest=content_hash,
        timestamp=anchor_timestamp,
    )

    tx_hash = _extract_chain_tx_hash(anchor_response)
    block_number = _extract_chain_block_number(anchor_response)
    contract_address = (
        anchor_response.get("contract_address")
        or settings.FISCO_CONTRACT_ADDRESS
    )
    chain_type = anchor_response.get("chain_type") or settings.FISCO_CHAIN_TYPE

    if not tx_hash:
        raise HTTPException(status_code=502, detail="FISCO 上链服务未返回 tx_hash")

    chain_record = ChainRecord(
        biz_type="task_result",
        biz_id=str(task_result.id),
        content_hash=content_hash,
        chain_type=chain_type,
        tx_hash=tx_hash,
        block_number=block_number,
        contract_address=contract_address,
        status="success",
        error_message=None,
    )

    db.add(chain_record)
    db.commit()
    db.refresh(chain_record)

    chain_record_data = _chain_record_to_dict(chain_record)

    audit_result_json = {
        "message": "任务结果真实上链存证成功",
        "task_id": task.id,
        "task_code": task.task_code,
        "task_name": task.task_name,
        "result_id": task_result.id,
        "result_hash": task_result.result_hash,
        "content_hash": content_hash,
        "chain_anchor_task_id": anchor_task_id,
        "chain_record_id": chain_record.id,
        "chain_type": chain_record.chain_type,
        "tx_hash": chain_record.tx_hash,
        "block_number": chain_record.block_number,
        "contract_address": chain_record.contract_address,
        "status": chain_record.status,
        "verify_result": anchor_response.get("verify_result"),
    }

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_RESULT_CHAIN_ANCHOR",
        object_type="chain_record",
        object_id=str(chain_record.id),
        task_id=task.id,
        operation_desc="任务结果真实上链存证",
        request_json={
            "task_id": task.id,
            "result_id": task_result.id,
            "biz_type": "task_result",
            "content_hash": content_hash,
            "chain_anchor_task_id": anchor_task_id,
            "anchor_service_url": settings.FISCO_ANCHOR_SERVICE_URL,
        },
        result_json=audit_result_json,
    )

    data = {
        "anchored": True,
        "duplicated": False,
        "message": "任务结果真实上链存证成功",
        "anchor_payload": anchor_payload,
        "anchor_response": {
            "success": anchor_response.get("success"),
            "chain_type": chain_type,
            "contract_address": contract_address,
            "tx_hash": tx_hash,
            "block_number": block_number,
            "status": anchor_response.get("status"),
            "verify_result": anchor_response.get("verify_result"),
            "chain_result": anchor_response.get("chain_result"),
        },
        "chain_record": chain_record_data,
    }

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.post("/{task_id}/run")
def run_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    执行任务。

    第二十三阶段：
    - statistic：调用 Alice SecretFlow 联合统计服务，生成真实联合统计结果；
    - federated_learning：调用 Alice SecretFlow 联邦训练服务，生成真实训练结果。
    """
    task = task_service.get_task_or_404(db=db, task_id=task_id)
    params_json = _safe_json_dict(getattr(task, "params_json", None))
    task_type = params_json.get("task_type") or "statistic"

    if task_type == "federated_learning":
        data = _run_secretflow_federated_learning_task(
            db=db,
            task=task,
        )
    else:
        data = _run_secretflow_statistic_task(
            db=db,
            task=task,
        )

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
            "executor": (
                "secretflow_fl"
                if audit_result_json.get("task_type") == "federated_learning"
                else "secretflow"
            ),
        },
        result_json=audit_result_json,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }

