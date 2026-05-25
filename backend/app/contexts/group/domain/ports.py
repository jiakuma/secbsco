from abc import ABC, abstractmethod
from typing import Any
from .models import GroupInfo, GroupMember, GroupNodeAuth, GroupDatasetAuth, GroupTemplateAuth


class GroupRepository(ABC):
    @abstractmethod
    def get_by_id(self, group_id: int) -> GroupInfo | None: ...

    @abstractmethod
    def get_by_code(self, group_code: str) -> GroupInfo | None: ...

    @abstractmethod
    def list_groups(self, *, accessible_ids=None, keyword=None, status=None, region_code=None, page=1, page_size=10) -> tuple[list[GroupInfo], int]: ...

    @abstractmethod
    def save(self, group: GroupInfo) -> GroupInfo: ...

    @abstractmethod
    def delete(self, group_id: int) -> None: ...

    @abstractmethod
    def count_members(self, group_id: int) -> int: ...

    @abstractmethod
    def count_users(self, group_id: int) -> int: ...

    @abstractmethod
    def count_nodes(self, group_id: int) -> int: ...

    @abstractmethod
    def count_tasks(self, group_id: int) -> int: ...


class GroupMemberRepository(ABC):
    @abstractmethod
    def list_members(self, group_id: int) -> list[GroupMember]: ...

    @abstractmethod
    def get_member(self, group_id: int, agency_id: int) -> GroupMember | None: ...

    @abstractmethod
    def save_member(self, member: GroupMember) -> GroupMember: ...

    @abstractmethod
    def remove_member(self, group_id: int, agency_id: int) -> None: ...


class GroupNodeRepository(ABC):
    @abstractmethod
    def list_nodes(self, group_id: int, node_type=None, node_usage_role=None, auth_status=None) -> list[dict]: ...

    @abstractmethod
    def list_available_nodes(self, group_id: int, visible_agency_ids=None) -> list[dict]: ...

    @abstractmethod
    def get_node_auth(self, group_id: int, node_id: int) -> GroupNodeAuth | None: ...

    @abstractmethod
    def save_node_auth(self, auth: GroupNodeAuth) -> GroupNodeAuth: ...

    @abstractmethod
    def remove_node_auth(self, group_id: int, node_id: int) -> None: ...


class GroupDatasetRepository(ABC):
    @abstractmethod
    def list_datasets(self, group_id: int) -> list[dict]: ...

    @abstractmethod
    def list_available_datasets(self, group_id: int, visible_agency_ids=None) -> list[dict]: ...

    @abstractmethod
    def get_dataset_auth(self, group_id: int, dataset_id: int) -> GroupDatasetAuth | None: ...

    @abstractmethod
    def save_dataset_auth(self, auth: GroupDatasetAuth) -> GroupDatasetAuth: ...

    @abstractmethod
    def remove_dataset_auth(self, group_id: int, dataset_id: int) -> None: ...


class GroupTemplateRepository(ABC):
    @abstractmethod
    def list_templates(self, group_id: int) -> list[dict]: ...

    @abstractmethod
    def list_available_templates(self, group_id: int, visible_agency_ids=None) -> list[dict]: ...

    @abstractmethod
    def get_template_auth(self, group_id: int, template_id: int) -> GroupTemplateAuth | None: ...

    @abstractmethod
    def save_template_auth(self, auth: GroupTemplateAuth) -> GroupTemplateAuth: ...

    @abstractmethod
    def remove_template_auth(self, group_id: int, template_id: int) -> None: ...


class AccessControlPort(ABC):
    @abstractmethod
    def get_accessible_group_ids(self, current_user) -> list[int] | None: ...

    @abstractmethod
    def check_group_access(self, current_user, group_id: int) -> None: ...

    @abstractmethod
    def check_group_admin_access(self, current_user, group_id: int) -> None: ...

    @abstractmethod
    def is_platform_admin(self, user_id: int) -> bool: ...

    @abstractmethod
    def is_agency_admin(self, user_id: int) -> bool: ...

    @abstractmethod
    def get_visible_agency_ids(self, current_user) -> list[int] | None: ...

    @abstractmethod
    def can_approve_group(self, current_user, group) -> bool: ...

    @abstractmethod
    def find_common_parent_agency(self, agency_id_1: int, agency_id_2: int) -> int | None: ...


class AuditLogPort(ABC):
    @abstractmethod
    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type=None, resource_id=None, agency_id=None, group_id=None, request=None) -> None: ...

    @abstractmethod
    def write_lifecycle_log(self, db, group_id, event_type, operator_user_id, operator_name, before_status=None, after_status=None, reason=None) -> None: ...


class UserQueryPort(ABC):
    @abstractmethod
    def list_group_users(self, group_id: int) -> list[dict]: ...

    @abstractmethod
    def add_group_user(self, group_id: int, user_id: int, role_code: str, current_user) -> dict: ...

    @abstractmethod
    def update_group_user_role(self, group_id: int, user_id: int, role_code: str, current_user) -> dict: ...

    @abstractmethod
    def remove_group_user(self, group_id: int, user_id: int, current_user) -> dict: ...


class AgencyQueryPort(ABC):
    @abstractmethod
    def get_agency_name(self, agency_id: int | None) -> str | None: ...

    @abstractmethod
    def get_agency_by_id(self, agency_id: int) -> Any | None: ...


class LifecycleLogRepository(ABC):
    @abstractmethod
    def list_logs(self, group_id: int) -> list[dict]: ...
