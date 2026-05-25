from abc import ABC, abstractmethod
from typing import Optional
from .models import AuditLogInfo


class AuditLogRepository(ABC):
    @abstractmethod
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
        ...

    @abstractmethod
    def get_by_id(self, log_id: int) -> Optional[AuditLogInfo]:
        ...
