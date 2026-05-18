"""
群组生命周期日志服务。

提供群组生命周期日志的查询功能。
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.group import GroupLifecycleLog


def list_lifecycle_logs(
    db: Session,
    group_id: int,
    event_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    查询群组生命周期日志（分页）。

    Returns:
        {"items": [...], "total": int}
    """
    query = (
        db.query(GroupLifecycleLog)
        .filter(GroupLifecycleLog.group_id == group_id)
    )

    if event_type:
        query = query.filter(GroupLifecycleLog.event_type == event_type)

    total = query.count()
    logs = (
        query
        .order_by(desc(GroupLifecycleLog.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "group_id": log.group_id,
            "event_type": log.event_type,
            "before_status": log.before_status,
            "after_status": log.after_status,
            "operator_user_id": log.operator_user_id,
            "operator_name": log.operator_name,
            "reason": log.reason,
            "detail_json": log.detail_json,
            "created_at": _format_dt(log.created_at),
        })

    return {"items": items, "total": total}


def _format_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")
