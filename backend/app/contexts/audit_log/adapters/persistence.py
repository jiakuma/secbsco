from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog as AuditLogORM
from ..domain.models import AuditLogInfo
from ..domain.ports import AuditLogRepository


def _to_domain(orm: AuditLogORM) -> AuditLogInfo:
    return AuditLogInfo(
        id=orm.id,
        task_id=orm.task_id,
        agency_id=orm.agency_id,
        operator_user_id=orm.operator_user_id,
        operation_type=orm.operation_type,
        object_type=orm.object_type,
        object_id=orm.object_id,
        operation_desc=orm.operation_desc,
        request_json=orm.request_json,
        result_json=orm.result_json,
        ip_address=orm.ip_address,
        created_at=orm.created_at,
    )


class SQLAlchemyAuditLogRepository(AuditLogRepository):
    def __init__(self, db: Session):
        self._db = db

    def list_logs(
        self,
        task_id: Optional[int] = None,
        agency_id: Optional[int] = None,
        operator_user_id: Optional[int] = None,
        operation_type: Optional[str] = None,
        object_type: Optional[str] = None,
        object_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[AuditLogInfo]]:
        query = self._db.query(AuditLogORM)
        if task_id:
            query = query.filter(AuditLogORM.task_id == task_id)
        if agency_id:
            query = query.filter(AuditLogORM.agency_id == agency_id)
        if operator_user_id:
            query = query.filter(AuditLogORM.operator_user_id == operator_user_id)
        if operation_type:
            query = query.filter(AuditLogORM.operation_type == operation_type)
        if object_type:
            query = query.filter(AuditLogORM.object_type == object_type)
        if object_id:
            query = query.filter(AuditLogORM.object_id == str(object_id))
        total = query.count()
        items = (
            query
            .order_by(AuditLogORM.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, [_to_domain(i) for i in items]

    def get_by_id(self, log_id: int) -> Optional[AuditLogInfo]:
        orm = self._db.query(AuditLogORM).filter(AuditLogORM.id == log_id).first()
        if not orm:
            return None
        return _to_domain(orm)
