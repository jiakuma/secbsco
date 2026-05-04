from datetime import date, datetime
from typing import Optional, Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit_log_schema import AuditLogCreate


def _to_jsonable(value: Any):
    """
    将 datetime 等对象转为 JSON 可保存格式，避免写入 MySQL JSON 字段时报错。
    """
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _to_jsonable(item)
            for item in value
        ]

    return value


class AuditLogService:

    @staticmethod
    def list_logs(
        db: Session,
        task_id: Optional[int] = None,
        agency_id: Optional[int] = None,
        operator_user_id: Optional[int] = None,
        operation_type: Optional[str] = None,
        object_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ):
        query = db.query(AuditLog)

        if task_id:
            query = query.filter(AuditLog.task_id == task_id)

        if agency_id:
            query = query.filter(AuditLog.agency_id == agency_id)

        if operator_user_id:
            query = query.filter(AuditLog.operator_user_id == operator_user_id)

        if operation_type:
            query = query.filter(AuditLog.operation_type == operation_type)

        if object_type:
            query = query.filter(AuditLog.object_type == object_type)

        total = query.count()

        items = (
            query
            .order_by(AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items

    @staticmethod
    def get_log_by_id(
        db: Session,
        log_id: int
    ) -> Optional[AuditLog]:
        return (
            db.query(AuditLog)
            .filter(AuditLog.id == log_id)
            .first()
        )

    @staticmethod
    def create_log(
        db: Session,
        log_req: AuditLogCreate
    ) -> AuditLog:
        log = AuditLog(
            task_id=log_req.task_id,
            agency_id=log_req.agency_id,
            operator_user_id=log_req.operator_user_id,
            operation_type=log_req.operation_type,
            object_type=log_req.object_type,
            object_id=log_req.object_id,
            operation_desc=log_req.operation_desc,
            request_json=_to_jsonable(log_req.request_json),
            result_json=_to_jsonable(log_req.result_json),
            ip_address=log_req.ip_address,
        )

        db.add(log)
        db.commit()
        db.refresh(log)

        return log

    @staticmethod
    def build_log_info(log: AuditLog) -> dict:
        return {
            "id": log.id,
            "task_id": log.task_id,
            "agency_id": log.agency_id,
            "operator_user_id": log.operator_user_id,
            "operation_type": log.operation_type,
            "object_type": log.object_type,
            "object_id": log.object_id,
            "operation_desc": log.operation_desc,
            "request_json": log.request_json,
            "result_json": log.result_json,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
        }