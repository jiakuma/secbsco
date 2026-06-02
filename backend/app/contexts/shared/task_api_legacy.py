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
from app.contexts.shared import task_service
from app.contexts.shared.access_control_service import (
    get_accessible_group_ids,
    check_group_access,
    check_task_run_access,
    is_platform_admin,
    write_operate_log,
)
from app.contexts.computation.adapters.secretflow_stat_client import SecretFlowStatService
from app.contexts.computation.adapters.secretflow_fl_client import SecretFlowFLService
from app.contexts.shared.task_result_service import TaskResultService
from app.schemas.audit_log_schema import AuditLogCreate
from app.contexts.shared.audit_log_service import AuditLogService
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


def _check_runtime_health(runtime_url: str, timeout: int = 5) -> bool:
    import requests
    try:
        resp = requests.get(f"{runtime_url}/health", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def _start_runtime_via_agent(agent_url: str, timeout: int = 30) -> dict:
    import requests
    try:
        resp = requests.post(
            f"{agent_url}/services/start",
            json={"service_code": "bio_task_runtime"},
            timeout=timeout,
        )
        return resp.json() if resp.status_code == 200 else {"success": False, "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def _ensure_bio_task_runtime_ready(agent_url: str | None = None) -> None:
    import time
    from app.core.config import settings

    runtime_url = settings.BIO_TASK_RUNTIME_URL
    agent_url_to_use = agent_url or settings.ALICE_NODE_AGENT_URL

    if _check_runtime_health(runtime_url):
        return

    result = _start_runtime_via_agent(agent_url_to_use, settings.ALICE_NODE_AGENT_TIMEOUT)

    if not result.get("success"):
        raise HTTPException(
            status_code=503,
            detail=f"启动 bio-task-runtime 失败：{result.get('message', '未知错误')}"
        )

    time.sleep(3)

    for _ in range(5):
        if _check_runtime_health(runtime_url):
            return
        time.sleep(2)

    raise HTTPException(
        status_code=503,
        detail="bio-task-runtime 启动超时，请检查 Alice 节点服务状态"
    )


def _run_bio_task_runtime(db: Session, task, template) -> dict:
    """
    调用 bio-task-runtime 18190 执行通用任务模板。

    当前支持：
    - T2_SPATIOTEMPORAL_TEMPLATE：跨区县传染病时空预测与共同暴露分析
    - T3_VACCINE_EFFECT_EVALUATION_TEMPLATE：疫苗安全效果持续评估
    - T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE：高血压危险因素交互作用安全分析
    """
    import requests
    from app.models.group import GroupDataset
    from app.models.agency import Agency
    from app.models.node import Node
    from app.models.dataset import Dataset
    from app.core.config import settings

    def _template_text_for_match() -> str:
        values = [
            getattr(template, "template_code", None),
            getattr(template, "template_name", None),
            getattr(template, "name", None),
            getattr(template, "scenario_name", None),
            getattr(template, "applicable_scenario", None),
            getattr(template, "output_type", None),
            getattr(template, "result_type", None),
            getattr(template, "description", None),
            getattr(task, "task_code", None),
            getattr(task, "task_name", None),
            getattr(task, "description", None),
            f"template_id={getattr(task, 'template_id', '')}",
        ]
        return " ".join(str(v) for v in values if v)

    def _is_t3_runtime_task() -> bool:
        text = _template_text_for_match()
        return (
            "T3_VACCINE_EFFECT_EVALUATION_TEMPLATE" in text
            or "疫苗安全效果持续评估" in text
            or "疫苗效果评估" in text
            or ("疫苗" in text and ("VE" in text or "保护效果" in text or "接种" in text))
        )

    def _is_t4_runtime_task() -> bool:
        text = _template_text_for_match()
        return (
            "T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE" in text
            or "T4_HYPERTENSION" in text
            or "高血压危险因素交互作用" in text
            or "高血压危险因素交互分析" in text
            or ("高血压" in text and ("交互" in text or "危险因素" in text or "OR" in text or "回归" in text))
            or "template_id=7" in text
        )

    def _resolve_template_code() -> str:
        raw_code = getattr(template, "template_code", None) if template else None
        if _is_t4_runtime_task():
            # 前端新建模板时可能生成 TPL_xxx，这里强制映射到 Runtime 实际目录。
            return "T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE"
        if _is_t3_runtime_task():
            # 前端新建模板时可能生成 TPL_xxx，这里强制映射到 Runtime 实际目录。
            return "T3_VACCINE_EFFECT_EVALUATION_TEMPLATE"
        return raw_code or "T2_SPATIOTEMPORAL_TEMPLATE"

    def _resolve_party_code(agency, node, dataset, index: int) -> str:
        text = " ".join(
            str(v or "")
            for v in [
                getattr(agency, "agency_code", None),
                getattr(agency, "agency_name", None),
                getattr(node, "node_code", None),
                getattr(node, "node_name", None),
                getattr(dataset, "dataset_code", None),
                getattr(dataset, "dataset_name", None),
                getattr(dataset, "data_location", None),
            ]
        ).upper()

        if "ALICE" in text or "CHANGAN" in text or "长安" in text:
            return "alice"
        if "BOB" in text or "QIAOXI" in text or "桥西" in text:
            return "bob"
        if "CAROL" in text or "YUHUA" in text or "裕华" in text:
            return "carol"

        fallback = ["alice", "bob", "carol"]
        return fallback[index] if index < len(fallback) else f"party_{index + 1}"

    def _build_t3_task_context(participant_rows: list[dict], params_json: dict) -> dict:
        parties_for_runtime = []

        default_path_by_party = {
            "alice": "/data/t3/t3_changan_vaccine_eval.csv",
            "bob": "/data/t3/t3_qiaoxi_vaccine_eval.csv",
            "carol": "/data/t3/t3_yuhua_vaccine_eval.csv",
        }

        for item in participant_rows:
            party_code = item["party_code"]
            data_path = item.get("dataset_path") or default_path_by_party.get(party_code, "")

            parties_for_runtime.append(
                {
                    "party": party_code,
                    "party_name": item.get("district_name") or item.get("agency_name") or party_code,
                    "agency_code": item.get("agency_code"),
                    "district_code": item.get("district_code") or "",
                    "district_name": item.get("district_name") or item.get("agency_name") or "",
                    "data_path": data_path,
                }
            )

        # 固定顺序，避免前端添加参与方顺序不同导致 Runtime 展示顺序漂移。
        order = {"alice": 0, "bob": 1, "carol": 2}
        parties_for_runtime = sorted(
            parties_for_runtime,
            key=lambda x: order.get(x.get("party"), 99),
        )

        return {
            "task_id": task.id,
            "task_code": task.task_code or f"task_{task.id}",
            "task_name": task.task_name,
            "group_id": getattr(task, "group_id", None),
            "template_code": "T3_VACCINE_EFFECT_EVALUATION_TEMPLATE",
            "template_version": "1.0.0",
            "scenario_code": "T3_VACCINE_EFFECT_EVALUATION",
            "scenario_name": "疫苗安全效果持续评估",
            "region_code": params_json.get("region_code", "130100"),
            "region_name": params_json.get("region_name", "石家庄市"),
            "task_params": {
                "use_secretflow": params_json.get("use_secretflow", True),
                "ray_address": params_json.get("ray_address", "192.168.0.40:10001"),
                "region_code": params_json.get("region_code", "130100"),
                "region_name": params_json.get("region_name", "石家庄市"),
                "date_range": {
                    "start_date": params_json.get("start_date") or params_json.get(
                        "analysis_start_date") or "2026-04-01",
                    "end_date": params_json.get("end_date") or params_json.get("analysis_end_date") or "2026-04-30",
                },
                "disease_code": params_json.get("disease_code", "J10"),
                "disease_name": params_json.get("disease_name", "流感"),
                "method": params_json.get("method", "TND_OR_VE"),
            },
            "parties": parties_for_runtime,
        }

    def _build_t4_task_context(participant_rows: list[dict], params_json: dict) -> dict:
        parties_for_runtime = []

        default_path_by_party = {
            "alice": "/data/t4/t4_changan_hypertension_survey.csv",
            "bob": "/data/t4/t4_qiaoxi_hypertension_survey.csv",
            "carol": "/data/t4/t4_yuhua_hypertension_survey.csv",
        }

        default_district_by_party = {
            "alice": {"district_code": "130102", "district_name": "长安区", "agency_name": "长安区疾控中心"},
            "bob": {"district_code": "130104", "district_name": "桥西区", "agency_name": "桥西区疾控中心"},
            "carol": {"district_code": "130108", "district_name": "裕华区", "agency_name": "裕华区疾控中心"},
        }

        for item in participant_rows:
            party_code = item["party_code"]
            default_info = default_district_by_party.get(party_code, {})
            dataset_path = item.get("dataset_path") or default_path_by_party.get(party_code, "")

            parties_for_runtime.append(
                {
                    "party": party_code,
                    "party_name": item.get("district_name") or default_info.get("district_name") or party_code,
                    "agency_name": item.get("agency_name") or default_info.get("agency_name") or "",
                    "district_code": item.get("district_code") or default_info.get("district_code") or "",
                    "district_name": item.get("district_name") or default_info.get("district_name") or "",
                    "dataset_path": dataset_path,
                }
            )

        # 固定顺序，避免前端添加参与方顺序不同导致 Runtime 展示顺序漂移。
        order = {"alice": 0, "bob": 1, "carol": 2}
        parties_for_runtime = sorted(
            parties_for_runtime,
            key=lambda x: order.get(x.get("party"), 99),
        )

        return {
            "task_id": task.id,
            "task_code": task.task_code or f"task_{task.id}",
            "task_name": task.task_name,
            "group_id": getattr(task, "group_id", None),
            "template_code": "T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE",
            "template_version": "1.0.0",
            "scenario_code": "T4_HYPERTENSION_FACTOR_INTERACTION_ANALYSIS",
            "scenario_name": "高血压危险因素交互作用安全分析",
            "ray_address": params_json.get("ray_address", "192.168.0.40:10001"),
            "stat_period": {
                "start_date": params_json.get("start_date") or params_json.get("analysis_start_date") or "2026-04-01",
                "end_date": params_json.get("end_date") or params_json.get("analysis_end_date") or "2026-04-30",
            },
            "params": {
                "target_disease": "hypertension",
                "target_field": "hypertension_flag",
                "analysis_name": "高血压危险因素交互作用安全分析",
            },
            "parties": parties_for_runtime,
        }

    # 0. 查询参与方并确保 bio-task-runtime 服务可用
    parties = (
        db.query(TaskParty)
        .filter(TaskParty.task_id == task.id)
        .order_by(TaskParty.id.asc())
        .all()
    )

    if not parties:
        raise HTTPException(status_code=400, detail="任务参与方为空，无法执行任务")

    agent_url = None
    for party in parties:
        if party.node_id:
            node = db.query(Node).filter(Node.id == party.node_id).first()
            if node and node.agent_url:
                agent_url = node.agent_url
                break

    _ensure_bio_task_runtime_ready(agent_url)

    # 1. 组装 participants，同时为 T3 生成 party 映射。
    participants = []
    participant_rows = []

    for index, party in enumerate(parties):
        agency = db.query(Agency).filter(Agency.id == party.agency_id).first()
        node = db.query(Node).filter(Node.id == party.node_id).first() if party.node_id else None
        dataset = db.query(Dataset).filter(Dataset.id == party.dataset_id).first() if party.dataset_id else None

        if not agency:
            raise HTTPException(status_code=400, detail=f"参与方机构不存在：agency_id={party.agency_id}")

        roles = []
        if party.party_role:
            roles = [r.strip() for r in party.party_role.split(",") if r.strip()]

        if "data_provider" in roles and not dataset:
            raise HTTPException(
                status_code=400,
                detail=f"数据提供方缺少数据集配置：agency={agency.agency_name}"
            )

        party_code = _resolve_party_code(agency=agency, node=node, dataset=dataset, index=index)

        participant = {
            "agency_code": agency.agency_code or f"AGENCY_{agency.id}",
            "agency_name": agency.agency_name,
            "district_code": agency.region_code or "",
            "district_name": agency.region_name or "",
            "node_code": node.node_code if node else "",
            "node_name": node.node_name if node else "",
            "dataset_name": dataset.dataset_name if dataset else "",
            "dataset_path": dataset.data_location if dataset else "",
            "roles": roles,
        }
        participants.append(participant)

        participant_rows.append(
            {
                **participant,
                "party_code": party_code,
            }
        )

    # 2. 查找辅助数据集。T2 会用到；T3 不依赖，但保留不影响。
    group_id = task.group_id
    auxiliary_datasets = {
        "grid_daily_stats_path": "",
        "grid_catalog_path": "",
    }

    if group_id:
        group_datasets = db.query(GroupDataset).filter(
            GroupDataset.group_id == group_id,
            GroupDataset.auth_status == "active",
        ).all()

        for gd in group_datasets:
            ds = db.query(Dataset).filter(Dataset.id == gd.dataset_id).first()
            if not ds:
                continue

            if "grid_daily_stats" in (ds.dataset_type or "") or "空间网格日统计" in (ds.dataset_name or ""):
                auxiliary_datasets["grid_daily_stats_path"] = ds.data_location or ""

            if "grid_catalog" in (ds.dataset_type or "") or "空间网格目录" in (ds.dataset_name or ""):
                auxiliary_datasets["grid_catalog_path"] = ds.data_location or ""

    # 3. 组装 task_context
    params_json = _safe_json_dict(getattr(task, "params_json", None))
    template_code = _resolve_template_code()
    is_t3_task = template_code == "T3_VACCINE_EFFECT_EVALUATION_TEMPLATE"
    is_t4_task = template_code == "T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE"

    if is_t3_task:
        task_context = _build_t3_task_context(participant_rows=participant_rows, params_json=params_json)
        task_result_type = "vaccine_effect_evaluation"
    elif is_t4_task:
        task_context = _build_t4_task_context(participant_rows=participant_rows, params_json=params_json)
        task_result_type = "hypertension_factor_interaction"
    else:
        task_context = {
            "task_id": task.id,
            "task_name": task.task_name,
            "group_id": group_id,
            "template_code": template_code,
            "template_version": "1.0.0",
            "scenario_code": "infectious_spatiotemporal_prediction",
            "disease_code": "J10.1",
            "disease_name": "流感",
            "participants": participants,
            "auxiliary_datasets": auxiliary_datasets,
            "params": {
                "analysis_start_date": params_json.get("analysis_start_date", "2026-04-01"),
                "analysis_end_date": params_json.get("analysis_end_date", "2026-04-30"),
                "recent_window_days": params_json.get("recent_window_days", 7),
                "prediction_window_days": params_json.get("prediction_window_days", 7),
                "top_grid_n": params_json.get("top_grid_n", 10),
                "common_exposure_min_cases": params_json.get("common_exposure_min_cases", 6),
            },
        }
        task_result_type = "spatiotemporal_prediction"

    # 4. 更新任务状态为运行中
    task.status = "running"
    for party in parties:
        party.status = "running"
        party.error_message = None
    db.commit()

    # 5. 调用 bio-task-runtime
    runtime_url = settings.BIO_TASK_RUNTIME_URL
    timeout = settings.BIO_TASK_RUNTIME_TIMEOUT

    try:
        response = requests.post(
            f"{runtime_url}/tasks/run",
            json={
                "task_context": task_context,
                "timeout_seconds": timeout,
            },
            timeout=timeout + 10,
        )

        if response.status_code != 200:
            task.status = "failed"
            for party in parties:
                party.status = "failed"
                party.error_message = f"任务运行服务返回错误：HTTP {response.status_code}"
            db.commit()
            raise HTTPException(
                status_code=502,
                detail=f"任务运行服务返回错误：HTTP {response.status_code}, {response.text[:500]}"
            )

        runtime_result = response.json()

        runtime_str = str(runtime_result)
        print(f"[DEBUG] Runtime response (first 3000 chars): {runtime_str[:3000]}")

    except requests.exceptions.ConnectionError:
        task.status = "failed"
        for party in parties:
            party.status = "failed"
            party.error_message = "任务运行服务不可用，请检查 bio-task-runtime 18190"
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="任务运行服务不可用，请检查 bio-task-runtime 18190"
        )
    except requests.exceptions.Timeout:
        task.status = "failed"
        for party in parties:
            party.status = "failed"
            party.error_message = f"任务执行超时（{timeout}秒）"
        db.commit()
        raise HTTPException(
            status_code=504,
            detail=f"任务执行超时（{timeout}秒）"
        )
    except Exception as e:
        task.status = "failed"
        for party in parties:
            party.status = "failed"
            party.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"调用任务运行服务失败：{str(e)}")

    # 6. 检查 runtime 返回结果
    result = runtime_result.get("result") or {}
    runtime_success = (
        runtime_result.get("success") is True
        and runtime_result.get("status", "success") == "success"
        and isinstance(result, dict)
        and bool(result)
    )

    result_hash = (
        runtime_result.get("result_hash")
        or result.get("result_hash")
        or _calc_sha256(result)
    )
    message = runtime_result.get("message", "")

    print(
        f"[DEBUG] Runtime success check: success={runtime_result.get('success')}, "
        f"status={runtime_result.get('status')}, result_exists={bool(result)}"
    )
    print(f"[DEBUG] runtime_success={runtime_success}")

    def _build_runtime_metrics(result_json: dict) -> dict:
        if is_t3_task:
            summary = _safe_json_dict(result_json.get("summary"))
            overall_effect = _safe_json_dict(result_json.get("overall_effect"))
            return {
                "scenario_code": result_json.get("scenario_code"),
                "scenario_name": result_json.get("scenario_name"),
                "template_code": result_json.get("template_code"),
                "framework": _safe_json_dict(result_json.get("execution_info")).get("framework"),
                "execution_mode": _safe_json_dict(result_json.get("execution_info")).get("execution_mode"),
                "total_count": summary.get("total_count"),
                "positive_count": summary.get("positive_count"),
                "negative_count": summary.get("negative_count"),
                "vaccinated_count": summary.get("vaccinated_count"),
                "unvaccinated_count": summary.get("unvaccinated_count"),
                "vaccination_rate": summary.get("vaccination_rate"),
                "positive_rate": summary.get("positive_rate"),
                "overall_ve": summary.get("overall_ve"),
                "or_value": overall_effect.get("or_value"),
                "participant_count": len(result_json.get("participants") or []),
            }

        if is_t4_task:
            summary = _safe_json_dict(result_json.get("summary"))
            execution_info = _safe_json_dict(result_json.get("execution_info"))
            return {
                "scenario_code": result_json.get("scenario_code"),
                "scenario_name": result_json.get("scenario_name"),
                "template_code": result_json.get("template_code"),
                "framework": result_json.get("framework") or execution_info.get("framework"),
                "execution_mode": result_json.get("execution_mode") or execution_info.get("execution_mode"),
                "total_count": summary.get("total_count"),
                "hypertension_count": summary.get("hypertension_count"),
                "hypertension_rate": summary.get("hypertension_rate"),
                "hypertension_rate_percent": summary.get("hypertension_rate_percent"),
                "high_risk_count": summary.get("high_risk_count"),
                "high_risk_rate": summary.get("high_risk_rate"),
                "top_single_factor": summary.get("top_single_factor"),
                "top_single_factor_or": summary.get("top_single_factor_or"),
                "top_interaction_factor": summary.get("top_interaction_factor"),
                "top_interaction_factor_or": summary.get("top_interaction_factor_or"),
                "participant_count": len(result_json.get("participants") or []),
            }

        return {
            "scenario_code": result_json.get("scenario_code"),
            "scenario_name": result_json.get("scenario_name"),
            "case_count": result_json.get("case_count"),
            "positive_count": result_json.get("positive_count"),
            "positive_rate": result_json.get("positive_rate"),
            "unique_patient_count": result_json.get("unique_patient_count"),
            "framework": result_json.get("framework"),
        }

    # 7. 写入结果（失败或成功均更新/插入 task_result）
    existing_result = db.query(TaskResult).filter(TaskResult.task_id == task.id).first()

    if existing_result:
        existing_result.result_json = result if runtime_success else runtime_result
        existing_result.metrics_json = _build_runtime_metrics(result) if runtime_success else {}
        existing_result.result_hash = result_hash
        existing_result.status = "success" if runtime_success else "failed"
        existing_result.error_message = None if runtime_success else message
        existing_result.group_id = group_id
        existing_result.agency_id = task.creator_agency_id or task.lead_agency_id
        existing_result.task_type = task_result_type
        existing_result.anchor_status = None
        existing_result.anchor_time = None
        existing_result.chain_record_id = None
        if hasattr(existing_result, "result_version"):
            existing_result.result_version = (existing_result.result_version or 1) + 1
        if hasattr(existing_result, "updated_at"):
            existing_result.updated_at = datetime.now()
        task_result = existing_result
    else:
        task_result = TaskResult(
            task_id=task.id,
            result_json=result if runtime_success else runtime_result,
            metrics_json=_build_runtime_metrics(result) if runtime_success else {},
            result_hash=result_hash,
            status="success" if runtime_success else "failed",
            error_message=None if runtime_success else message,
            group_id=group_id,
            agency_id=task.creator_agency_id or task.lead_agency_id,
            task_type=task_result_type,
            result_version=1,
        )
        db.add(task_result)

    if runtime_success:
        task.status = "success"
        for party in parties:
            party.status = "success"
            party.error_message = None
    else:
        task.status = "failed"
        for party in parties:
            party.status = "failed"
            party.error_message = message

    if hasattr(task, "updated_at"):
        task.updated_at = datetime.now()

    db.commit()
    db.refresh(task)
    db.refresh(task_result)

    if not runtime_success:
        return {
            "task": task_service.task_to_dict(task),
            "parties": [task_service.party_to_dict(party) for party in parties],
            "result": _task_result_to_dict(task_result),
            "runtime_request": task_context,
            "runtime_response": runtime_result,
            "message": message or "任务执行失败",
        }

    print(f"[SUCCESS] Task {task.id} executed successfully, result_id={task_result.id}, result_hash={result_hash}")

    return {
        "task": task_service.task_to_dict(task),
        "parties": [task_service.party_to_dict(party) for party in parties],
        "result": _task_result_to_dict(task_result),
        "runtime_request": task_context,
        "runtime_response": {
            "success": runtime_result.get("success"),
            "status": runtime_result.get("status"),
            "message": runtime_result.get("message"),
            "result_hash": result_hash,
            "duration_seconds": runtime_result.get("duration_seconds", 0),
        },
        "message": "Bio Task Runtime 任务执行成功，已生成结果",
    }


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
    group_id: int | None = Query(default=None, description="群组ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # 权限过滤
    accessible_group_ids = get_accessible_group_ids(db, current_user.id)

    # 如果指定了 group_id，校验用户是否可访问
    if group_id is not None:
        check_group_access(db, current_user.id, group_id)

    data = task_service.list_tasks(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
        group_id=group_id,
        accessible_group_ids=accessible_group_ids,
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
    4. 必须绑定 group_id，且用户必须有该群组访问权限。
    """
    if not task_create.group_id:
        raise HTTPException(status_code=400, detail="任务必须绑定群组，请先选择群组")

    check_group_access(db, current_user.id, task_create.group_id)

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

    # 权限校验：检查任务群组
    task_group_id = data.get("group_id")
    if task_group_id:
        check_group_access(db, current_user.id, task_group_id)

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
    """
    创建任务参与方。

    校验规则：
    1. 参与机构必须是任务所属群组的成员机构
    2. 节点必须是该群组已授权的节点
    3. 数据提供方必须选择数据资源，后端自动解析dataset_id
    """
    from app.models.group import GroupMember, GroupNode, GroupDataset
    from app.models.dataset import Dataset

    task = task_service.get_task_or_404(db, task_id)
    group_id = getattr(task, "group_id", None)

    if not group_id:
        raise HTTPException(status_code=400, detail="任务未绑定群组，无法添加参与方")

    check_group_access(db, current_user.id, group_id)

    if party_create.agency_id:
        is_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.agency_id == party_create.agency_id,
            GroupMember.join_status == "active",
        ).first()
        if not is_member:
            raise HTTPException(status_code=400, detail="参与机构不在群组成员机构中")

    if party_create.node_id:
        is_authorized_node = db.query(GroupNode).filter(
            GroupNode.group_id == group_id,
            GroupNode.node_id == party_create.node_id,
            GroupNode.auth_status == "active",
        ).first()
        if not is_authorized_node:
            raise HTTPException(status_code=400, detail="节点未授权给该群组，请先在群组中授权节点")

    party_role = getattr(party_create, 'party_role', '') or ''
    roles = [r.strip() for r in party_role.split(',') if r.strip()]
    has_data_provider = 'data_provider' in roles

    data_resource_name = getattr(party_create, 'data_resource_name', None)

    if has_data_provider:
        if not party_create.dataset_id and not data_resource_name:
            raise HTTPException(status_code=400, detail="数据提供方必须选择数据资源")

        if not party_create.dataset_id and data_resource_name:
            dataset_query = db.query(Dataset).join(
                GroupDataset,
                GroupDataset.dataset_id == Dataset.id
            ).filter(
                GroupDataset.group_id == group_id,
                GroupDataset.auth_status == "active",
                Dataset.agency_id == party_create.agency_id,
                Dataset.dataset_name == data_resource_name,
            )

            if party_create.node_id:
                dataset_query = dataset_query.filter(Dataset.node_id == party_create.node_id)

            matching_datasets = dataset_query.all()

            if not matching_datasets:
                node_hint = f"、节点ID={party_create.node_id}" if party_create.node_id else ""
                raise HTTPException(
                    status_code=400,
                    detail=f"未找到匹配的数据集：机构ID={party_create.agency_id}{node_hint}、数据资源名称='{data_resource_name}'。请检查数据集是否已授权给当前群组，或联系管理员添加数据授权。"
                )

            if len(matching_datasets) > 1:
                dataset_ids = [d.id for d in matching_datasets]
                raise HTTPException(
                    status_code=400,
                    detail=f"数据资源匹配到多条记录（dataset_id={dataset_ids}），请检查数据集名称、机构和节点配置是否唯一。建议联系管理员检查数据集配置。"
                )

            party_create.dataset_id = matching_datasets[0].id

    party_columns = {column.name for column in TaskParty.__table__.columns}
    party_data = party_create.model_dump()
    filtered_party_data = {k: v for k, v in party_data.items() if k in party_columns}

    data = task_service.create_task_party(
        db=db,
        task_id=task_id,
        party_data=filtered_party_data,
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


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    删除任务（物理删除）。

    删除任务时会级联删除：
    1. audit_log 审计日志
    2. chain_record 链上记录
    3. task_party 参与方记录
    4. task_result 结果记录

    注意：此操作不可恢复。
    """
    from sqlalchemy import text

    task = task_service.get_task_or_404(db=db, task_id=task_id)

    # 权限校验：检查任务群组
    task_group_id = getattr(task, "group_id", None)
    if task_group_id:
        check_group_access(db, current_user.id, task_group_id)

    task_name = task.task_name

    try:
        # 按照外键依赖顺序删除，先删子表，再删主表

        # 1. 删除 audit_log（有外键约束）
        db.execute(
            text("DELETE FROM audit_log WHERE task_id = :task_id"),
            {"task_id": task_id}
        )

        # 2. 删除 chain_record（可能有 task_id 引用）
        db.execute(
            text("DELETE FROM chain_record WHERE task_id = :task_id"),
            {"task_id": task_id}
        )

        # 3. 删除 task_party（有外键约束）
        db.query(TaskParty).filter(TaskParty.task_id == task_id).delete()

        # 4. 删除 task_result（有外键约束）
        db.query(TaskResult).filter(TaskResult.task_id == task_id).delete()

        # 5. 最后删除 task 主表
        db.delete(task)

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除任务失败：{str(e)}")

    # 写入审计日志（在删除后重新创建一条记录）
    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_DELETE",
        object_type="task",
        object_id=str(task_id),
        task_id=None,  # 任务已删除，设为 None
        operation_desc=f"删除任务：{task_name}",
        request_json={"task_id": task_id},
        result_json={"deleted": True},
    )

    return {
        "code": 0,
        "message": "success",
        "data": {"task_id": task_id, "deleted": True},
    }


@router.post("/{task_id}/chain-anchor")
def anchor_task_result(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    任务结果手动上链存证（补偿接口）。

    当前实现方式：
    1. 调用 BlockchainAnchorService 服务层进行上链；
    2. 写入 TASK_RESULT_CHAIN_ANCHOR 审计日志；
    3. 保持与自动上链相同的幂等性检查和错误处理。
    """
    from app.services.blockchain_anchor_service import BlockchainAnchorService

    # 调用服务层进行手动上链
    result = BlockchainAnchorService.anchor_task_result(
        db=db,
        task_id=task_id,
        trigger_mode="manual"
    )

    # 检查服务层返回结果
    if result["code"] != 200:
        raise HTTPException(
            status_code=result["code"],
            detail=result["message"]
        )

    data = result["data"]

    # 记录审计日志
    audit_result_json = {
        "message": result["message"],
        "task_id": task_id,
        "result_id": data.get("result_id"),
        "result_hash": data.get("result_hash"),
        "tx_hash": data.get("tx_hash"),
        "block_number": data.get("block_number"),
        "contract_address": data.get("contract_address"),
        "chain_record_id": data.get("chain_record_id"),
        "trigger_mode": data.get("trigger_mode", "manual"),
        "already_anchored": data.get("already_anchored", False),
        "success": data.get("success", False)
    }

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_RESULT_CHAIN_ANCHOR",
        object_type="chain_record",
        object_id=str(data.get("chain_record_id", "")),
        task_id=task_id,
        operation_desc="任务结果手动上链存证",
        request_json={
            "task_id": task_id,
            "trigger_mode": "manual"
        },
        result_json=audit_result_json,
    )

    return {
        "code": 0,
        "message": result["message"],
        "data": {
            "anchored": data.get("success", False),
            "duplicated": data.get("already_anchored", False),
            "message": result["message"],
            "task_id": task_id,
            "result_id": data.get("result_id"),
            "result_hash": data.get("result_hash"),
            "tx_hash": data.get("tx_hash"),
            "block_number": data.get("block_number"),
            "contract_address": data.get("contract_address"),
            "chain_record_id": data.get("chain_record_id"),
            "trigger_mode": data.get("trigger_mode", "manual")
        },
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

    第九阶段：支持 T2 任务调用 bio-task-runtime 18190。
    第二十三阶段：
    - statistic：调用 Alice SecretFlow 联合统计服务，生成真实联合统计结果；
    - federated_learning：调用 Alice SecretFlow 联邦训练服务，生成真实训练结果。
    """
    from app.models.stat_template import StatTemplate
    from app.contexts.computation.adapters.execution_engine import (
        run_bio_task_runtime,
        run_secretflow_federated_learning_task,
        run_secretflow_statistic_task,
        build_task_run_audit_desc,
        build_task_run_audit_result,
        _safe_json_dict as _safe_json_dict_ext,
    )

    task = task_service.get_task_or_404(db=db, task_id=task_id)

    check_task_run_access(db, current_user.id, getattr(task, "group_id", None))

    template = None
    if task.template_id:
        template = db.query(StatTemplate).filter(StatTemplate.id == task.template_id).first()

    template_code = template.template_code if template else None
    params_json = _safe_json_dict_ext(getattr(task, "params_json", None))
    task_type = params_json.get("task_type") or "statistic"

    template_text = " ".join(
        str(v)
        for v in [
            template_code,
            getattr(template, "template_name", None) if template else None,
            getattr(template, "name", None) if template else None,
            getattr(template, "output_type", None) if template else None,
            getattr(template, "result_type", None) if template else None,
            getattr(template, "applicable_scenario", None) if template else None,
            getattr(task, "task_code", None),
            getattr(task, "task_name", None),
            getattr(task, "description", None),
            f"template_id={getattr(task, 'template_id', '')}",
        ]
        if v
    )

    is_runtime_task = (
        (template_code and template_code.startswith("T2"))
        or "T2_SPATIOTEMPORAL_TEMPLATE" in template_text
        or "T3_VACCINE_EFFECT_EVALUATION_TEMPLATE" in template_text
        or "疫苗安全效果持续评估" in template_text
        or "疫苗效果评估" in template_text
        or ("疫苗" in template_text and ("保护效果" in template_text or "接种" in template_text))
        or "T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE" in template_text
        or "T4_HYPERTENSION" in template_text
        or "高血压危险因素交互作用" in template_text
        or "高血压危险因素交互分析" in template_text
        or ("高血压" in template_text and (
            "交互" in template_text or "危险因素" in template_text or "OR" in template_text or "回归" in template_text))
        or "template_id=7" in template_text
    )

    if is_runtime_task:
        data = run_bio_task_runtime(
            db=db,
            task=task,
            template=template,
        )
    elif task_type == "federated_learning":
        data = run_secretflow_federated_learning_task(
            db=db,
            task=task,
        )
    else:
        data = run_secretflow_statistic_task(
            db=db,
            task=task,
        )

    operation_desc = build_task_run_audit_desc(data)
    audit_result_json = build_task_run_audit_result(data)

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
                "bio_task_runtime"
                if is_runtime_task
                else (
                    "secretflow_fl"
                    if audit_result_json.get("task_type") == "federated_learning"
                    else "secretflow"
                )
            ),
        },
        result_json=audit_result_json,
    )

    # 任务执行成功后，触发自动上链
    # 说明：
    # 1. 不再只依赖 data["result"]["status"]，因为部分执行链路返回体中 result.status 可能缺失；
    # 2. 以数据库中最新成功 task_result 为准，只要存在成功结果且 result_hash 不为空，就触发自动上链；
    # 3. 自动上链失败不影响任务执行结果，仅记录日志。
    try:
        from app.services.blockchain_anchor_service import BlockchainAnchorService
        from app.models.task_result import TaskResult

        latest_success_result = (
            db.query(TaskResult)
            .filter(
                TaskResult.task_id == task_id,
                TaskResult.status == "success",
                TaskResult.result_hash.isnot(None),
            )
            .order_by(TaskResult.updated_at.desc(), TaskResult.id.desc())
            .first()
        )

        if latest_success_result:
            BlockchainAnchorService.trigger_auto_anchor_on_task_success(
                db=db,
                task_id=task_id,
            )
            print(
                f"[INFO] 任务 {task_id} 结果自动上链已触发，"
                f"result_id={latest_success_result.id}, "
                f"result_hash={latest_success_result.result_hash}"
            )
        else:
            task_info = data.get("task") or {}
            result_info = data.get("result") or {}
            print(
                f"[INFO] 任务 {task_id} 未触发自动上链："
                f"task_status={task_info.get('status')}, "
                f"result_status={result_info.get('status')}, "
                f"未找到成功且带 result_hash 的 task_result"
            )
    except Exception as e:
        print(f"[WARNING] 任务 {task_id} 结果自动上链触发失败: {e}")
        # 不抛出异常，不影响任务执行结果

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }

