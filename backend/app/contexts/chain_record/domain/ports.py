from abc import ABC, abstractmethod
from typing import Optional, Any
from .models import ChainRecordInfo, RelatedTaskInfo


class ChainRecordRepository(ABC):
    @abstractmethod
    def list_records(
        self,
        biz_type: Optional[str] = None,
        biz_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[ChainRecordInfo]]:
        ...

    @abstractmethod
    def get_by_id(self, record_id: int) -> Optional[ChainRecordInfo]:
        ...

    @abstractmethod
    def mock_anchor_content(self, biz_type: str, biz_id: str, content: dict) -> Any:
        ...


class RelatedTaskPort(ABC):
    @abstractmethod
    def build_related_task(self, biz_type: str, biz_id: str) -> Optional[RelatedTaskInfo]:
        ...


class TaskLookupPort(ABC):
    @abstractmethod
    def get_by_id(self, task_id: int) -> Optional[RelatedTaskInfo]:
        ...


class AuditLogLookupPort(ABC):
    @abstractmethod
    def get_by_id(self, log_id: int) -> Any:
        ...


class TaskResultLookupPort(ABC):
    @abstractmethod
    def get_by_id(self, result_id: int) -> Any:
        ...
