from abc import ABC, abstractmethod
from typing import Optional
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


class RelatedTaskPort(ABC):
    @abstractmethod
    def build_related_task(self, biz_type: str, biz_id: str) -> Optional[RelatedTaskInfo]:
        ...
