from abc import ABC, abstractmethod
from typing import Any
from .models import User


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    def list_users(self, *, manageable_ids=None, keyword=None, status=None, agency_id=None, role_code=None, page=1, page_size=10) -> tuple[list[User], int]: ...

    @abstractmethod
    def save(self, user: User) -> User: ...

    @abstractmethod
    def delete(self, user_id: int) -> None: ...


class AuthPort(ABC):
    @abstractmethod
    def authenticate(self, username: str, password: str, db=None) -> User | None: ...

    @abstractmethod
    def hash_password(self, password: str) -> str: ...

    @abstractmethod
    def create_token(self, user_id: int, username: str) -> str: ...


class AccessControlPort(ABC):
    @abstractmethod
    def get_user_context(self, user_id: int) -> dict: ...

    @abstractmethod
    def get_accessible_group_ids(self, user_id: int) -> list[int] | None: ...

    @abstractmethod
    def check_group_admin_access(self, user_id: int, group_id: int) -> None: ...

    @abstractmethod
    def is_platform_admin(self, user_id: int) -> bool: ...

    @abstractmethod
    def get_manageable_agency_ids(self, current_user: Any) -> list[int] | None: ...

    @abstractmethod
    def require_agency_in_scope(self, current_user: Any, agency_id: int) -> None: ...

    @abstractmethod
    def check_can_manage_user(self, current_user: Any, target_user_id: int) -> None: ...


class AuditLogPort(ABC):
    @abstractmethod
    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type=None, resource_id=None, agency_id=None, group_id=None, request=None) -> None: ...

    @abstractmethod
    def anchor_resource_operation(self, db, *, resource_type, resource_id, operation_type, operator, agency_id=None, before_data=None, after_data=None) -> Any: ...


class MenuPort(ABC):
    @abstractmethod
    def get_menus_for_roles(self, roles: list[dict]) -> list[dict]: ...


class RoleBindingPort(ABC):
    @abstractmethod
    def get_user_roles(self, user_id: int) -> list[dict]: ...

    @abstractmethod
    def bind_role(self, user_id: int, role_code: str, scope_type: str, scope_id: int | None, current_user: Any, request=None) -> dict: ...

    @abstractmethod
    def unbind_role(self, binding_id: int) -> None: ...


class UserGroupPort(ABC):
    @abstractmethod
    def get_user_groups(self, user_id: int) -> list[dict]: ...

    @abstractmethod
    def add_user_to_group(self, user_id: int, group_id: int, agency_id: int | None, current_user: Any, request=None) -> dict: ...

    @abstractmethod
    def remove_user_from_group(self, user_id: int, group_id: int) -> None: ...


class AgencyQueryPort(ABC):
    @abstractmethod
    def get_agency_name(self, agency_id: int | None) -> str | None: ...
