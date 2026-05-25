from abc import ABC, abstractmethod
from typing import Any
from .models import Agency


class AgencyRepository(ABC):
    @abstractmethod
    def get_by_id(self, agency_id: int) -> Agency | None: ...

    @abstractmethod
    def get_by_code(self, agency_code: str) -> Agency | None: ...

    @abstractmethod
    def list_agencies(
        self,
        manageable_ids: list[int] | None = None,
        keyword: str | None = None,
        agency_level: str | None = None,
        agency_type: str | None = None,
        status: str | None = None,
        parent_agency_id: int | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Agency], int]: ...

    @abstractmethod
    def get_agency_tree(self, manageable_ids: list[int] | None = None) -> list[dict]: ...

    @abstractmethod
    def save(self, agency: Agency) -> Agency: ...

    @abstractmethod
    def delete(self, agency_id: int) -> dict: ...

    @abstractmethod
    def get_agency_and_descendant_ids(self, root_agency_id: int) -> list[int]: ...

    @abstractmethod
    def get_agency_name(self, agency_id: int | None) -> str | None: ...

    @abstractmethod
    def get_summary(self, agency_id: int) -> dict: ...


class AgencyPermissionPort(ABC):
    @abstractmethod
    def get_manageable_agency_ids(self, current_user: Any) -> list[int] | None: ...

    @abstractmethod
    def check_can_create_child_agency(self, current_user: Any, parent_agency_id: int | None, agency_level: str | None) -> None: ...

    @abstractmethod
    def check_can_manage_agency(self, current_user: Any, agency_id: int) -> None: ...


class AgencyAuditPort(ABC):
    @abstractmethod
    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type, resource_id, agency_id, request=None) -> None: ...

    @abstractmethod
    def anchor_resource_operation(self, db, *, resource_type, resource_id, operation_type, operator, agency_id=None, before_data=None, after_data=None) -> Any: ...
