from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.agency import Agency
from app.models.node import Node
from app.models.dataset import Dataset
from app.models.stat_template import StatTemplate
from app.models.task import Task
from app.models.task_result import TaskResult
from app.models.audit_log import AuditLog
from app.models.chain_record import ChainRecord


def _safe_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 50:
        return 50
    return limit


def _count(db: Session, model, *conditions) -> int:
    stmt = select(func.count(model.id))

    for condition in conditions:
        stmt = stmt.where(condition)

    return int(db.execute(stmt).scalar_one() or 0)


def get_dashboard_summary(db: Session) -> dict:
    return {
        "agency_count": _count(db, Agency),
        "node_count": _count(db, Node),
        "dataset_count": _count(db, Dataset),
        "stat_template_count": _count(db, StatTemplate),
        "task_count": _count(db, Task),
        "success_task_count": _count(db, Task, Task.status == "success"),
        "result_count": _count(db, TaskResult),
        "audit_log_count": _count(db, AuditLog),
        "chain_record_count": _count(db, ChainRecord),
    }


def get_recent_tasks(db: Session, limit: int = 5) -> list[dict]:
    limit = _safe_limit(limit)

    stmt = (
        select(Task)
        .order_by(desc(Task.created_at))
        .limit(limit)
    )

    rows = db.execute(stmt).scalars().all()

    return [
        {
            "id": item.id,
            "task_code": item.task_code,
            "task_name": item.task_name,
            "creator_user_id": item.creator_user_id,
            "creator_agency_id": item.creator_agency_id,
            "template_id": item.template_id,
            "stat_start_time": item.stat_start_time,
            "stat_end_time": item.stat_end_time,
            "status": item.status,
            "description": item.description,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        for item in rows
    ]


def get_recent_results(db: Session, limit: int = 5) -> list[dict]:
    limit = _safe_limit(limit)

    stmt = (
        select(TaskResult)
        .order_by(desc(TaskResult.created_at))
        .limit(limit)
    )

    rows = db.execute(stmt).scalars().all()

    return [
        {
            "id": item.id,
            "task_id": item.task_id,
            "result_json": item.result_json,
            "metrics_json": item.metrics_json,
            "result_hash": item.result_hash,
            "status": item.status,
            "error_message": item.error_message,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        for item in rows
    ]


def get_recent_audit_logs(db: Session, limit: int = 5) -> list[dict]:
    limit = _safe_limit(limit)

    stmt = (
        select(AuditLog)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )

    rows = db.execute(stmt).scalars().all()

    return [
        {
            "id": item.id,
            "task_id": item.task_id,
            "agency_id": item.agency_id,
            "operator_user_id": item.operator_user_id,
            "operation_type": item.operation_type,
            "object_type": item.object_type,
            "object_id": item.object_id,
            "operation_desc": item.operation_desc,
            "request_json": item.request_json,
            "result_json": item.result_json,
            "ip_address": item.ip_address,
            "created_at": item.created_at,
        }
        for item in rows
    ]


def get_recent_chain_records(db: Session, limit: int = 5) -> list[dict]:
    limit = _safe_limit(limit)

    stmt = (
        select(ChainRecord)
        .order_by(desc(ChainRecord.created_at))
        .limit(limit)
    )

    rows = db.execute(stmt).scalars().all()

    return [
        {
            "id": item.id,
            "biz_type": item.biz_type,
            "biz_id": item.biz_id,
            "content_hash": item.content_hash,
            "chain_type": item.chain_type,
            "tx_hash": item.tx_hash,
            "block_number": item.block_number,
            "contract_address": item.contract_address,
            "status": item.status,
            "error_message": item.error_message,
            "created_at": item.created_at,
        }
        for item in rows
    ]