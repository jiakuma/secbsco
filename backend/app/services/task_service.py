from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.task_party import TaskParty
from app.schemas.task_schema import (
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskPartyCreate,
    TaskPartyUpdate,
)


def _model_dump(schema):
    return schema.model_dump(exclude_unset=True)


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
) -> dict:
    query = db.query(Task)

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


def create_task(db: Session, task_create: TaskCreate) -> dict:
    exists = db.query(Task).filter(Task.task_code == task_create.task_code).first()
    if exists:
        raise HTTPException(status_code=400, detail="任务编码已存在")

    task = Task(**task_create.model_dump())
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
    task = get_task_or_404(db, task_id)

    parties = (
        db.query(TaskParty)
        .filter(TaskParty.task_id == task_id)
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