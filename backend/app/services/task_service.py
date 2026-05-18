from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.task_party import TaskParty
from app.models.task_result import TaskResult
from app.schemas.task_schema import (
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskPartyCreate,
    TaskPartyUpdate,
)


def _model_dump(schema):
    return schema.model_dump(exclude_unset=True)


def _safe_load_json(value: Any) -> dict:
    """
    兼容 params_json 可能是 dict 或 str 的情况。
    """
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}

    return {}


def _get_task_type(task: Task) -> str:
    """
    从 task.params_json 中识别任务类型。
    历史任务默认按联合统计处理。
    """
    params = _safe_load_json(getattr(task, "params_json", None))
    return params.get("task_type") or "statistic"


def task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "task_code": task.task_code,
        "task_name": task.task_name,
        "creator_user_id": task.creator_user_id,
        "creator_agency_id": task.creator_agency_id,
        "template_id": task.template_id,
        "stat_start_time": task.stat_start_time,
        "stat_end_time": task.stat_end_time,
        "params_json": task.params_json,
        "status": task.status,
        "description": task.description,
        "group_id": getattr(task, "group_id", None),
        "lead_agency_id": getattr(task, "lead_agency_id", None),
        "execution_mode": getattr(task, "execution_mode", None),
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def party_to_dict(party: TaskParty) -> dict:
    return {
        "id": party.id,
        "task_id": party.task_id,
        "agency_id": party.agency_id,
        "node_id": party.node_id,
        "dataset_id": party.dataset_id,
        "party_role": party.party_role,
        "field_mapping_json": party.field_mapping_json,
        "status": party.status,
        "error_message": party.error_message,
        "created_at": party.created_at,
        "updated_at": party.updated_at,
    }


def get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def list_tasks(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    status: str | None = None,
    keyword: str | None = None,
    group_id: int | None = None,
    accessible_group_ids: list[int] | None = None,
) -> dict:
    """
    任务列表（支持权限过滤）。

    Args:
        accessible_group_ids: 可访问的群组 ID 列表，None 代表全局可访问。
    """
    query = db.query(Task)

    # 权限过滤：仅返回可访问群组下的任务
    if accessible_group_ids is not None:
        query = query.filter(
            (Task.group_id.in_(accessible_group_ids)) | (Task.group_id.is_(None))
        )

    # 指定群组过滤
    if group_id is not None:
        query = query.filter(Task.group_id == group_id)

    if status:
        query = query.filter(Task.status == status)

    if keyword:
        query = query.filter(Task.task_name.like(f"%{keyword}%"))

    total = query.count()

    items = (
        query.order_by(Task.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [task_to_dict(item) for item in items],
    }


def create_task(
    db: Session,
    task_create: TaskCreate,
    creator_user_id: int | None = None,
    creator_agency_id: int | None = None,
) -> dict:
    exists = db.query(Task).filter(Task.task_code == task_create.task_code).first()
    if exists:
        raise HTTPException(status_code=400, detail="任务编码已存在")

    task_data = task_create.model_dump()

    # 创建人用户 ID：后端从当前登录用户写入，不依赖前端
    task_data["creator_user_id"] = creator_user_id

    # 创建机构：优先使用前端选择；没选时用当前用户机构兜底
    if not task_data.get("creator_agency_id"):
        task_data["creator_agency_id"] = creator_agency_id

    task = Task(**task_data)

    db.add(task)
    db.commit()
    db.refresh(task)

    return task_to_dict(task)


def get_task_detail(db: Session, task_id: int) -> dict:
    task = get_task_or_404(db, task_id)

    parties = (
        db.query(TaskParty)
        .filter(TaskParty.task_id == task_id)
        .order_by(TaskParty.id.asc())
        .all()
    )

    data = task_to_dict(task)
    data["parties"] = [party_to_dict(party) for party in parties]

    return data


def update_task(db: Session, task_id: int, task_update: TaskUpdate) -> dict:
    task = get_task_or_404(db, task_id)

    update_data = _model_dump(task_update)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)

    return task_to_dict(task)


def update_task_status(db: Session, task_id: int, status_update: TaskStatusUpdate) -> dict:
    task = get_task_or_404(db, task_id)

    task.status = status_update.status

    db.commit()
    db.refresh(task)

    return task_to_dict(task)


def list_task_parties(db: Session, task_id: int) -> list[dict]:
    get_task_or_404(db, task_id)

    parties = (
        db.query(TaskParty)
        .filter(TaskParty.task_id == task_id)
        .order_by(TaskParty.id.asc())
        .all()
    )

    return [party_to_dict(party) for party in parties]


def create_task_party(db: Session, task_id: int, party_create: TaskPartyCreate) -> dict:
    get_task_or_404(db, task_id)

    exists = (
        db.query(TaskParty)
        .filter(
            TaskParty.task_id == task_id,
            TaskParty.agency_id == party_create.agency_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="该机构已配置为任务参与方")

    party = TaskParty(
        task_id=task_id,
        **party_create.model_dump(),
    )

    db.add(party)
    db.commit()
    db.refresh(party)

    return party_to_dict(party)


def update_task_party(
    db: Session,
    task_id: int,
    party_id: int,
    party_update: TaskPartyUpdate,
) -> dict:
    get_task_or_404(db, task_id)

    party = (
        db.query(TaskParty)
        .filter(TaskParty.id == party_id, TaskParty.task_id == task_id)
        .first()
    )

    if not party:
        raise HTTPException(status_code=404, detail="任务参与方不存在")

    update_data = _model_dump(party_update)
    for key, value in update_data.items():
        setattr(party, key, value)

    db.commit()
    db.refresh(party)

    return party_to_dict(party)


def delete_task_party(db: Session, task_id: int, party_id: int) -> dict:
    get_task_or_404(db, task_id)

    party = (
        db.query(TaskParty)
        .filter(TaskParty.id == party_id, TaskParty.task_id == task_id)
        .first()
    )

    if not party:
        raise HTTPException(status_code=404, detail="任务参与方不存在")

    db.delete(party)
    db.commit()

    return {
        "deleted": True,
        "party_id": party_id,
    }


def mock_run_task(db: Session, task_id: int) -> dict:
    """
    任务执行统一入口：
    - statistic：原 Mock 联合统计
    - federated_learning：Mock 联邦训练
    """
    task = get_task_or_404(db, task_id)
    task_type = _get_task_type(task)

    if task_type == "federated_learning":
        return _mock_run_federated_learning_task(db=db, task=task)

    return _mock_run_statistic_task(db=db, task=task)


def _mock_run_statistic_task(db: Session, task: Task) -> dict:
    """
    原有 Mock 联合统计任务执行逻辑。
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

    task.status = "success"
    for party in parties:
        party.status = "success"

    db.commit()
    db.refresh(task)

    return {
        "task": task_to_dict(task),
        "parties": [party_to_dict(party) for party in parties],
        "message": "Mock 联合统计任务执行成功",
    }


def _mock_run_federated_learning_task(db: Session, task: Task) -> dict:
    """
    Mock 联邦学习训练任务执行逻辑。
    当前阶段不接入真实 Flower / SecretFlow，只生成模拟训练轮次和指标。
    """
    params = _safe_load_json(getattr(task, "params_json", None))

    parties = (
        db.query(TaskParty)
        .filter(TaskParty.task_id == task.id)
        .order_by(TaskParty.id.asc())
        .all()
    )

    if not parties:
        raise HTTPException(
            status_code=400,
            detail="当前联邦学习任务尚未配置训练节点，无法执行",
        )

    task.status = "running"
    for party in parties:
        party.status = "running"
        party.error_message = None

    db.commit()

    train_config = params.get("train_config") or {}
    epochs = int(train_config.get("epochs") or 5)

    scenario_code = params.get("scenario_code") or "infectious_spatiotemporal_prediction"
    scenario_name = params.get("scenario_name") or "跨区县传染病时空预测与疫情溯源"
    model_type = params.get("model_type") or "mock_spatiotemporal_model"
    framework = params.get("framework") or "mock"

    rounds = []
    base_loss = 0.72
    base_accuracy = 0.68
    base_auc = 0.72

    for i in range(1, epochs + 1):
        loss = round(max(0.18, base_loss - i * 0.08), 4)
        accuracy = round(min(0.95, base_accuracy + i * 0.042), 4)
        auc = round(min(0.97, base_auc + i * 0.04), 4)

        rounds.append(
            {
                "round": i,
                "loss": loss,
                "accuracy": accuracy,
                "auc": auc,
            }
        )

    final_round = rounds[-1]
    participant_count = len(parties)

    result_json = {
        "task_type": "federated_learning",
        "scenario_code": scenario_code,
        "scenario_name": scenario_name,
        "model_type": model_type,
        "framework": framework,
        "rounds": rounds,
        "summary": {
            "final_accuracy": final_round["accuracy"],
            "final_loss": final_round["loss"],
            "final_auc": final_round["auc"],
            "round_count": epochs,
            "participant_count": participant_count,
            "sample_count": participant_count * 925,
            "privacy_mode": "secure_aggregation",
            "raw_data_export": False,
        },
    }

    metrics_json = {
        "final_accuracy": final_round["accuracy"],
        "final_loss": final_round["loss"],
        "final_auc": final_round["auc"],
        "round_count": epochs,
        "participant_count": participant_count,
    }

    result_hash = hashlib.sha256(
        json.dumps(result_json, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

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

        if hasattr(task_result, "updated_at"):
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

    task.status = "success"

    for party in parties:
        party.status = "success"
        party.error_message = None

    if hasattr(task, "updated_at"):
        task.updated_at = now

    db.commit()
    db.refresh(task)
    db.refresh(task_result)

    return {
        "task": task_to_dict(task),
        "parties": [party_to_dict(party) for party in parties],
        "result": {
            "id": task_result.id,
            "task_id": task_result.task_id,
            "result_json": task_result.result_json,
            "metrics_json": task_result.metrics_json,
            "result_hash": task_result.result_hash,
            "status": task_result.status,
            "error_message": task_result.error_message,
            "created_at": task_result.created_at,
            "updated_at": task_result.updated_at,
        },
        "message": "Mock 联邦学习训练任务执行成功",
    }