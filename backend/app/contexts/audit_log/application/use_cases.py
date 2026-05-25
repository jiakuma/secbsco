from typing import Optional
from ..domain.ports import AuditLogRepository
from ..domain.models import AuditLogInfo
from ..domain.exceptions import AuditLogNotFoundError, raise_audit_log_not_found
from .dtos import AuditLogDTO, AuditLogPageDTO


def _to_dto(info: AuditLogInfo) -> AuditLogDTO:
    return AuditLogDTO(
        id=info.id,
        task_id=info.task_id,
        agency_id=info.agency_id,
        operator_user_id=info.operator_user_id,
        operation_type=info.operation_type,
        object_type=info.object_type,
        object_id=info.object_id,
        operation_desc=info.operation_desc,
        request_json=info.request_json,
        result_json=info.result_json,
        ip_address=info.ip_address,
        created_at=info.created_at,
    )


class ListAuditLogsUseCase:
    def __init__(self, repo: AuditLogRepository):
        self._repo = repo

    def execute(
        self,
        task_id: Optional[int] = None,
        agency_id: Optional[int] = None,
        operator_user_id: Optional[int] = None,
        operation_type: Optional[str] = None,
        object_type: Optional[str] = None,
        object_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> AuditLogPageDTO:
        total, items = self._repo.list_logs(
            task_id=task_id,
            agency_id=agency_id,
            operator_user_id=operator_user_id,
            operation_type=operation_type,
            object_type=object_type,
            object_id=object_id,
            page=page,
            page_size=page_size,
        )
        return AuditLogPageDTO(
            total=total,
            page=page,
            page_size=page_size,
            items=[_to_dto(i) for i in items],
        )


class GetAuditLogUseCase:
    def __init__(self, repo: AuditLogRepository):
        self._repo = repo

    def execute(self, log_id: int) -> AuditLogDTO:
        info = self._repo.get_by_id(log_id)
        if not info:
            raise_audit_log_not_found(log_id)
        return _to_dto(info)
