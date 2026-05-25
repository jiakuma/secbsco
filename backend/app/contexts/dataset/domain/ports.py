from abc import ABC, abstractmethod
from .models import DatasetInfo


class DatasetRepository(ABC):
    @abstractmethod
    def get_by_id(self, dataset_id: int) -> DatasetInfo | None: ...

    @abstractmethod
    def get_by_code(self, dataset_code: str) -> DatasetInfo | None: ...

    @abstractmethod
    def list_datasets(self, *, visible_agency_ids=None, keyword=None, agency_id=None, page=1, page_size=10) -> tuple[list[DatasetInfo], int]: ...

    @abstractmethod
    def save(self, dataset: DatasetInfo) -> DatasetInfo: ...

    @abstractmethod
    def delete(self, dataset_id: int) -> None: ...


class AccessControlPort(ABC):
    @abstractmethod
    def get_visible_agency_ids(self, current_user) -> list[int] | None: ...

    @abstractmethod
    def check_dataset_access(self, current_user, dataset: DatasetInfo, require_write: bool = False) -> None: ...

    @abstractmethod
    def require_admin(self, current_user) -> None: ...


class AgencyQueryPort(ABC):
    @abstractmethod
    def get_agency_name(self, agency_id: int | None) -> str | None: ...


class NodeQueryPort(ABC):
    @abstractmethod
    def get_node_name(self, node_id: int | None) -> str | None: ...
