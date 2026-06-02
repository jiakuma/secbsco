import hashlib
import json
import time
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.task_result import TaskResult
from app.models.task_party import TaskParty
from app.core.config import settings
from app.contexts.shared import task_service


def _safe_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _safe_json_dict(value: Any) -> dict:
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
    if value is None:
        return default_value
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    text = str(value)
    return text[:10] if len(text) >= 10 else default_value


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


def _calc_sha256(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _build_secretflow_stat_request(task) -> dict:
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


def _create_or_update_secretflow_stat_result(
    db: Session, task, sf_payload: dict,
) -> TaskResult:
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
    task_result = db.query(TaskResult).filter(TaskResult.task_id == task.id).first()
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
            task_id=task.id, result_json=result_json,
            metrics_json=metrics_json, result_hash=result_hash,
            status="success", error_message=None,
        )
        db.add(task_result)
    return task_result


def _create_or_update_secretflow_fl_result(
    db: Session, task, sf_payload: dict,
) -> TaskResult:
    params_json = _safe_json_dict(getattr(task, "params_json", None))
    result_json = _safe_json_dict(sf_payload.get("result"))
    metrics = _safe_json_dict(result_json.get("metrics"))
    training_params = _safe_json_dict(result_json.get("training_params"))
    participants = result_json.get("participants") or []
    if not isinstance(participants, list):
        participants = []
    summary = _safe_json_dict(result_json.get("summary"))
    summary.update({
        "final_accuracy": summary.get("final_accuracy") or metrics.get("accuracy"),
        "final_auc": summary.get("final_auc") or metrics.get("auc"),
        "final_precision": summary.get("final_precision") or metrics.get("precision"),
        "final_recall": summary.get("final_recall") or metrics.get("recall"),
        "final_f1": summary.get("final_f1") or metrics.get("f1"),
        "round_count": summary.get("round_count") or training_params.get("epochs"),
        "participant_count": summary.get("participant_count") or len(participants),
        "sample_count": summary.get("sample_count") or metrics.get("sample_count"),
        "privacy_mode": summary.get("privacy_mode") or result_json.get("aggregator") or result_json.get("partition_type"),
        "raw_data_export": False,
    })
    result_json.update({
        "task_type": "federated_learning",
        "task_id": task.task_code or f"task_{task.id}",
        "scenario_code": result_json.get("scenario_code") or params_json.get("scenario_code") or "flu_federated_learning",
        "scenario_name": result_json.get("scenario_name") or params_json.get("scenario_name") or "流感样病例联邦学习训练",
        "framework": result_json.get("framework") or "secretflow",
        "summary": summary,
    })
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
    result_hash = sf_payload.get("result_hash") or result_json.get("result_hash") or _calc_sha256(result_json)
    task_result = db.query(TaskResult).filter(TaskResult.task_id == task.id).first()
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
            task_id=task.id, result_json=result_json,
            metrics_json=metrics_json, result_hash=result_hash,
            status="success", error_message=None,
        )
        db.add(task_result)
    return task_result


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
    runtime_url = settings.BIO_TASK_RUNTIME_URL
    agent_url_to_use = agent_url or settings.ALICE_NODE_AGENT_URL
    if _check_runtime_health(runtime_url):
        return
    result = _start_runtime_via_agent(agent_url_to_use, settings.ALICE_NODE_AGENT_TIMEOUT)
    if not result.get("success"):
        raise HTTPException(status_code=503, detail=f"启动 bio-task-runtime 失败：{result.get('message', '未知错误')}")
    time.sleep(3)
    for _ in range(5):
        if _check_runtime_health(runtime_url):
            return
        time.sleep(2)
    raise HTTPException(status_code=503, detail="bio-task-runtime 启动超时，请检查 Alice 节点服务状态")


def run_secretflow_statistic_task(db: Session, task) -> dict:
    from .secretflow_stat_client import SecretFlowStatService
    parties = db.query(TaskParty).filter(TaskParty.task_id == task.id).order_by(TaskParty.id.asc()).all()
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
            task_id=sf_request["task_id"], start_date=sf_request["start_date"],
            end_date=sf_request["end_date"], syndrome_type=sf_request["syndrome_type"],
            alice_csv=sf_request["alice_csv"], bob_csv=sf_request["bob_csv"],
        )
        task_result = _create_or_update_secretflow_stat_result(db=db, task=task, sf_payload=sf_payload)
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
                "success": sf_payload.get("success"), "message": sf_payload.get("message"),
                "task_id": sf_payload.get("task_id"), "timestamp": sf_payload.get("timestamp"),
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


def run_secretflow_federated_learning_task(db: Session, task) -> dict:
    from .secretflow_fl_client import SecretFlowFLService
    parties = db.query(TaskParty).filter(TaskParty.task_id == task.id).order_by(TaskParty.id.asc()).all()
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
            task_id=fl_request["task_id"], train_mode=fl_request["train_mode"],
            alice_csv=fl_request["alice_csv"], bob_csv=fl_request["bob_csv"],
            epochs=fl_request["epochs"], batch_size=fl_request["batch_size"],
            learning_rate=fl_request["learning_rate"],
        )
        task_result = _create_or_update_secretflow_fl_result(db=db, task=task, sf_payload=sf_payload)
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
                "success": sf_payload.get("success"), "message": sf_payload.get("message"),
                "task_id": sf_payload.get("task_id"), "timestamp": sf_payload.get("timestamp"),
                "train_mode": sf_payload.get("train_mode"), "result_hash": sf_payload.get("result_hash"),
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


def run_bio_task_runtime(db: Session, task, template) -> dict:
    import requests
    from app.models.group import GroupDataset
    from app.models.agency import Agency
    from app.models.node import Node
    from app.models.dataset import Dataset

    def _template_text_for_match() -> str:
        values = [
            getattr(template, "template_code", None), getattr(template, "template_name", None),
            getattr(template, "name", None), getattr(template, "scenario_name", None),
            getattr(template, "applicable_scenario", None), getattr(template, "output_type", None),
            getattr(template, "result_type", None), getattr(template, "description", None),
            getattr(task, "task_code", None), getattr(task, "task_name", None),
            getattr(task, "description", None), f"template_id={getattr(task, 'template_id', '')}",
        ]
        return " ".join(str(v) for v in values if v)

    def _is_t3_runtime_task() -> bool:
        text = _template_text_for_match()
        return ("T3_VACCINE_EFFECT_EVALUATION_TEMPLATE" in text or "疫苗安全效果持续评估" in text
                or "疫苗效果评估" in text or ("疫苗" in text and ("VE" in text or "保护效果" in text or "接种" in text)))

    def _is_t4_runtime_task() -> bool:
        text = _template_text_for_match()
        return ("T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE" in text or "T4_HYPERTENSION" in text
                or "高血压危险因素交互作用" in text or "高血压危险因素交互分析" in text
                or ("高血压" in text and ("交互" in text or "危险因素" in text or "OR" in text or "回归" in text))
                or "template_id=7" in text)

    def _resolve_template_code() -> str:
        raw_code = getattr(template, "template_code", None) if template else None
        if _is_t4_runtime_task():
            return "T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE"
        if _is_t3_runtime_task():
            return "T3_VACCINE_EFFECT_EVALUATION_TEMPLATE"
        return raw_code or "T2_SPATIOTEMPORAL_TEMPLATE"

    def _resolve_party_code(agency, node, dataset, index: int) -> str:
        text = " ".join(str(v or "") for v in [
            getattr(agency, "agency_code", None), getattr(agency, "agency_name", None),
            getattr(node, "node_code", None), getattr(node, "node_name", None),
            getattr(dataset, "dataset_code", None), getattr(dataset, "dataset_name", None),
            getattr(dataset, "data_location", None),
        ]).upper()
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
        default_path_by_party = {"alice": "/data/t3/t3_changan_vaccine_eval.csv", "bob": "/data/t3/t3_qiaoxi_vaccine_eval.csv", "carol": "/data/t3/t3_yuhua_vaccine_eval.csv"}
        for item in participant_rows:
            party_code = item["party_code"]
            data_path = item.get("dataset_path") or default_path_by_party.get(party_code, "")
            parties_for_runtime.append({"party": party_code, "party_name": item.get("district_name") or item.get("agency_name") or party_code, "agency_code": item.get("agency_code"), "district_code": item.get("district_code") or "", "district_name": item.get("district_name") or item.get("agency_name") or "", "data_path": data_path})
        order = {"alice": 0, "bob": 1, "carol": 2}
        parties_for_runtime = sorted(parties_for_runtime, key=lambda x: order.get(x.get("party"), 99))
        return {"task_id": task.id, "task_code": task.task_code or f"task_{task.id}", "task_name": task.task_name, "group_id": getattr(task, "group_id", None), "template_code": "T3_VACCINE_EFFECT_EVALUATION_TEMPLATE", "template_version": "1.0.0", "scenario_code": "T3_VACCINE_EFFECT_EVALUATION", "scenario_name": "疫苗安全效果持续评估", "region_code": params_json.get("region_code", "130100"), "region_name": params_json.get("region_name", "石家庄市"), "task_params": {"use_secretflow": params_json.get("use_secretflow", True), "ray_address": params_json.get("ray_address", "192.168.0.40:10001"), "region_code": params_json.get("region_code", "130100"), "region_name": params_json.get("region_name", "石家庄市"), "date_range": {"start_date": params_json.get("start_date") or params_json.get("analysis_start_date") or "2026-04-01", "end_date": params_json.get("end_date") or params_json.get("analysis_end_date") or "2026-04-30"}, "disease_code": params_json.get("disease_code", "J10"), "disease_name": params_json.get("disease_name", "流感"), "method": params_json.get("method", "TND_OR_VE")}, "parties": parties_for_runtime}

    def _build_t4_task_context(participant_rows: list[dict], params_json: dict) -> dict:
        parties_for_runtime = []
        default_path_by_party = {"alice": "/data/t4/t4_changan_hypertension_survey.csv", "bob": "/data/t4/t4_qiaoxi_hypertension_survey.csv", "carol": "/data/t4/t4_yuhua_hypertension_survey.csv"}
        default_district_by_party = {"alice": {"district_code": "130102", "district_name": "长安区", "agency_name": "长安区疾控中心"}, "bob": {"district_code": "130104", "district_name": "桥西区", "agency_name": "桥西区疾控中心"}, "carol": {"district_code": "130108", "district_name": "裕华区", "agency_name": "裕华区疾控中心"}}
        for item in participant_rows:
            party_code = item["party_code"]
            default_info = default_district_by_party.get(party_code, {})
            dataset_path = item.get("dataset_path") or default_path_by_party.get(party_code, "")
            parties_for_runtime.append({"party": party_code, "party_name": item.get("district_name") or default_info.get("district_name") or party_code, "agency_name": item.get("agency_name") or default_info.get("agency_name") or "", "district_code": item.get("district_code") or default_info.get("district_code") or "", "district_name": item.get("district_name") or default_info.get("district_name") or "", "dataset_path": dataset_path})
        order = {"alice": 0, "bob": 1, "carol": 2}
        parties_for_runtime = sorted(parties_for_runtime, key=lambda x: order.get(x.get("party"), 99))
        return {"task_id": task.id, "task_code": task.task_code or f"task_{task.id}", "task_name": task.task_name, "group_id": getattr(task, "group_id", None), "template_code": "T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE", "template_version": "1.0.0", "scenario_code": "T4_HYPERTENSION_FACTOR_INTERACTION_ANALYSIS", "scenario_name": "高血压危险因素交互作用安全分析", "ray_address": params_json.get("ray_address", "192.168.0.40:10001"), "stat_period": {"start_date": params_json.get("start_date") or params_json.get("analysis_start_date") or "2026-04-01", "end_date": params_json.get("end_date") or params_json.get("analysis_end_date") or "2026-04-30"}, "params": {"target_disease": "hypertension", "target_field": "hypertension_flag", "analysis_name": "高血压危险因素交互作用安全分析"}, "parties": parties_for_runtime}

    parties = db.query(TaskParty).filter(TaskParty.task_id == task.id).order_by(TaskParty.id.asc()).all()
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
            raise HTTPException(status_code=400, detail=f"数据提供方缺少数据集配置：agency={agency.agency_name}")
        party_code = _resolve_party_code(agency=agency, node=node, dataset=dataset, index=index)
        participant = {"agency_code": agency.agency_code or f"AGENCY_{agency.id}", "agency_name": agency.agency_name, "district_code": agency.region_code or "", "district_name": agency.region_name or "", "node_code": node.node_code if node else "", "node_name": node.node_name if node else "", "dataset_name": dataset.dataset_name if dataset else "", "dataset_path": dataset.data_location if dataset else "", "roles": roles}
        participants.append(participant)
        participant_rows.append({**participant, "party_code": party_code})
    group_id = task.group_id
    auxiliary_datasets = {"grid_daily_stats_path": "", "grid_catalog_path": ""}
    if group_id:
        group_datasets = db.query(GroupDataset).filter(GroupDataset.group_id == group_id, GroupDataset.auth_status == "active").all()
        for gd in group_datasets:
            ds = db.query(Dataset).filter(Dataset.id == gd.dataset_id).first()
            if not ds:
                continue
            if "grid_daily_stats" in (ds.dataset_type or "") or "空间网格日统计" in (ds.dataset_name or ""):
                auxiliary_datasets["grid_daily_stats_path"] = ds.data_location or ""
            if "grid_catalog" in (ds.dataset_type or "") or "空间网格目录" in (ds.dataset_name or ""):
                auxiliary_datasets["grid_catalog_path"] = ds.data_location or ""
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
        task_context = {"task_id": task.id, "task_name": task.task_name, "group_id": group_id, "template_code": template_code, "template_version": "1.0.0", "scenario_code": "infectious_spatiotemporal_prediction", "disease_code": "J10.1", "disease_name": "流感", "participants": participants, "auxiliary_datasets": auxiliary_datasets, "params": {"analysis_start_date": params_json.get("analysis_start_date", "2026-04-01"), "analysis_end_date": params_json.get("analysis_end_date", "2026-04-30"), "recent_window_days": params_json.get("recent_window_days", 7), "prediction_window_days": params_json.get("prediction_window_days", 7), "top_grid_n": params_json.get("top_grid_n", 10), "common_exposure_min_cases": params_json.get("common_exposure_min_cases", 6)}}
        task_result_type = "spatiotemporal_prediction"
    task.status = "running"
    for party in parties:
        party.status = "running"
        party.error_message = None
    db.commit()
    runtime_url = settings.BIO_TASK_RUNTIME_URL
    timeout = settings.BIO_TASK_RUNTIME_TIMEOUT
    try:
        response = requests.post(f"{runtime_url}/tasks/run", json={"task_context": task_context, "timeout_seconds": timeout}, timeout=timeout + 10)
        if response.status_code != 200:
            task.status = "failed"
            for party in parties:
                party.status = "failed"
                party.error_message = f"任务运行服务返回错误：HTTP {response.status_code}"
            db.commit()
            raise HTTPException(status_code=502, detail=f"任务运行服务返回错误：HTTP {response.status_code}, {response.text[:500]}")
        runtime_result = response.json()
    except requests.exceptions.ConnectionError:
        task.status = "failed"
        for party in parties:
            party.status = "failed"
            party.error_message = "任务运行服务不可用，请检查 bio-task-runtime 18190"
        db.commit()
        raise HTTPException(status_code=502, detail="任务运行服务不可用，请检查 bio-task-runtime 18190")
    except requests.exceptions.Timeout:
        task.status = "failed"
        for party in parties:
            party.status = "failed"
            party.error_message = f"任务执行超时（{timeout}秒）"
        db.commit()
        raise HTTPException(status_code=504, detail=f"任务执行超时（{timeout}秒）")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        task.status = "failed"
        for party in parties:
            party.status = "failed"
            party.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"调用任务运行服务失败：{str(e)}")
    result = runtime_result.get("result") or {}
    runtime_success = (runtime_result.get("success") is True and runtime_result.get("status", "success") == "success" and isinstance(result, dict) and bool(result))
    result_hash = runtime_result.get("result_hash") or result.get("result_hash") or _calc_sha256(result)
    message = runtime_result.get("message", "")

    def _build_runtime_metrics(result_json: dict) -> dict:
        if is_t3_task:
            summary = _safe_json_dict(result_json.get("summary"))
            overall_effect = _safe_json_dict(result_json.get("overall_effect"))
            return {"scenario_code": result_json.get("scenario_code"), "scenario_name": result_json.get("scenario_name"), "template_code": result_json.get("template_code"), "framework": _safe_json_dict(result_json.get("execution_info")).get("framework"), "execution_mode": _safe_json_dict(result_json.get("execution_info")).get("execution_mode"), "total_count": summary.get("total_count"), "positive_count": summary.get("positive_count"), "negative_count": summary.get("negative_count"), "vaccinated_count": summary.get("vaccinated_count"), "unvaccinated_count": summary.get("unvaccinated_count"), "vaccination_rate": summary.get("vaccination_rate"), "positive_rate": summary.get("positive_rate"), "overall_ve": summary.get("overall_ve"), "or_value": overall_effect.get("or_value"), "participant_count": len(result_json.get("participants") or [])}
        if is_t4_task:
            summary = _safe_json_dict(result_json.get("summary"))
            execution_info = _safe_json_dict(result_json.get("execution_info"))
            return {"scenario_code": result_json.get("scenario_code"), "scenario_name": result_json.get("scenario_name"), "template_code": result_json.get("template_code"), "framework": result_json.get("framework") or execution_info.get("framework"), "execution_mode": result_json.get("execution_mode") or execution_info.get("execution_mode"), "total_count": summary.get("total_count"), "hypertension_count": summary.get("hypertension_count"), "hypertension_rate": summary.get("hypertension_rate"), "hypertension_rate_percent": summary.get("hypertension_rate_percent"), "high_risk_count": summary.get("high_risk_count"), "high_risk_rate": summary.get("high_risk_rate"), "top_single_factor": summary.get("top_single_factor"), "top_single_factor_or": summary.get("top_single_factor_or"), "top_interaction_factor": summary.get("top_interaction_factor"), "top_interaction_factor_or": summary.get("top_interaction_factor_or"), "participant_count": len(result_json.get("participants") or [])}
        return {"scenario_code": result_json.get("scenario_code"), "scenario_name": result_json.get("scenario_name"), "case_count": result_json.get("case_count"), "positive_count": result_json.get("positive_count"), "positive_rate": result_json.get("positive_rate"), "unique_patient_count": result_json.get("unique_patient_count"), "framework": result_json.get("framework")}

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
        task_result = TaskResult(task_id=task.id, result_json=result if runtime_success else runtime_result, metrics_json=_build_runtime_metrics(result) if runtime_success else {}, result_hash=result_hash, status="success" if runtime_success else "failed", error_message=None if runtime_success else message, group_id=group_id, agency_id=task.creator_agency_id or task.lead_agency_id, task_type=task_result_type, result_version=1)
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
        return {"task": task_service.task_to_dict(task), "parties": [task_service.party_to_dict(party) for party in parties], "result": _task_result_to_dict(task_result), "runtime_request": task_context, "runtime_response": runtime_result, "message": message or "任务执行失败"}
    return {"task": task_service.task_to_dict(task), "parties": [task_service.party_to_dict(party) for party in parties], "result": _task_result_to_dict(task_result), "runtime_request": task_context, "runtime_response": {"success": runtime_result.get("success"), "status": runtime_result.get("status"), "message": runtime_result.get("message"), "result_hash": result_hash, "duration_seconds": runtime_result.get("duration_seconds", 0)}, "message": "Bio Task Runtime 任务执行成功，已生成结果"}


def _get_task_type_from_run_data(data: dict) -> str:
    task = _safe_dict(data.get("task"))
    params_json = _safe_dict(task.get("params_json"))
    return params_json.get("task_type") or "statistic"


def build_task_run_audit_desc(data: dict) -> str:
    task_type = _get_task_type_from_run_data(data)
    if task_type == "federated_learning":
        return "执行 SecretFlow 联邦学习训练任务并生成训练结果"
    return "执行 SecretFlow 联合统计任务并生成统计结果"


def build_task_run_audit_result(data: dict) -> dict:
    task = _safe_dict(data.get("task"))
    result = _safe_dict(data.get("result"))
    params_json = _safe_dict(task.get("params_json"))
    result_json = _safe_dict(result.get("result_json"))
    metrics_json = _safe_dict(result.get("metrics_json"))
    summary = _safe_json_dict(result_json.get("summary"))
    task_type = params_json.get("task_type") or result_json.get("task_type") or "statistic"
    base_payload = {"task_id": task.get("id"), "task_code": task.get("task_code"), "task_name": task.get("task_name"), "task_type": task_type, "task_status": task.get("status"), "result_id": result.get("id"), "result_status": result.get("status"), "result_hash": result.get("result_hash"), "message": data.get("message")}
    if task_type == "federated_learning":
        return {**base_payload, "scenario_code": result_json.get("scenario_code") or params_json.get("scenario_code"), "scenario_name": result_json.get("scenario_name") or params_json.get("scenario_name"), "model_type": result_json.get("model_type") or params_json.get("model_type"), "framework": result_json.get("framework") or params_json.get("framework"), "round_count": summary.get("round_count") or metrics_json.get("round_count"), "participant_count": summary.get("participant_count") or metrics_json.get("participant_count"), "sample_count": summary.get("sample_count"), "final_accuracy": summary.get("final_accuracy") or metrics_json.get("final_accuracy"), "final_loss": summary.get("final_loss") or metrics_json.get("final_loss"), "final_auc": summary.get("final_auc") or metrics_json.get("final_auc"), "privacy_mode": summary.get("privacy_mode"), "raw_data_export": summary.get("raw_data_export")}
    return {**base_payload, "case_count": result_json.get("case_count") or metrics_json.get("case_count"), "unique_patient_count": result_json.get("unique_patient_count") or metrics_json.get("unique_patient_count"), "positive_count": result_json.get("positive_count") or metrics_json.get("positive_count"), "positive_rate": result_json.get("positive_rate") or metrics_json.get("positive_rate")}
