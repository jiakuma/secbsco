from abc import ABC, abstractmethod
from typing import Any
from .models import NodeInfo


class NodeRepository(ABC):
    @abstractmethod
    def get_by_id(self, node_id: int) -> NodeInfo | None: ...

    @abstractmethod
    def get_by_code(self, node_code: str) -> NodeInfo | None: ...

    @abstractmethod
    def list_nodes(self, *, manageable_ids=None, keyword=None, agency_id=None, status=None, node_type=None, page=1, page_size=10) -> tuple[list[NodeInfo], int]: ...

    @abstractmethod
    def save(self, node: NodeInfo) -> NodeInfo: ...

    @abstractmethod
    def delete(self, node_id: int) -> None: ...


class AccessControlPort(ABC):
    @abstractmethod
    def get_manageable_agency_ids(self, current_user) -> list[int] | None: ...

    @abstractmethod
    def require_agency_in_scope(self, current_user, agency_id: int) -> None: ...

    @abstractmethod
    def check_can_manage_node(self, current_user, node: Any) -> None: ...

    @abstractmethod
    def is_platform_admin(self, user_id: int) -> bool: ...


class AuditLogPort(ABC):
    @abstractmethod
    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type=None, resource_id=None, agency_id=None, group_id=None, request=None) -> None: ...

    @abstractmethod
    def anchor_resource_operation(self, db, *, resource_type, resource_id, operation_type, operator, agency_id=None, before_data=None, after_data=None) -> Any: ...


class AgencyQueryPort(ABC):
    @abstractmethod
    def get_agency_by_id(self, agency_id: int | None) -> Any | None: ...

    @abstractmethod
    def get_agency_name(self, agency_id: int | None) -> str | None: ...


class AgentPort(ABC):
    @abstractmethod
    def check_status(self, agent_url: str, agent_token: str | None) -> dict: ...

    @abstractmethod
    def activate(self, agent_url: str, agent_token: str | None) -> dict: ...

    @abstractmethod
    def deactivate(self, agent_url: str, agent_token: str | None) -> dict: ...
