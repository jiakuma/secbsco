from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UserDTO:
    id: int
    username: str
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    agency_id: int | None = None
    agency_name: str | None = None
    status: str = "active"
    last_login_time: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class LoginResultDTO:
    access_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 0
    user: dict = field(default_factory=dict)


@dataclass
class UserContextDTO:
    id: int = 0
    username: str = ""
    real_name: str | None = None
    agency_id: int | None = None
    agency_name: str | None = None
    current_group_id: int | None = None
    roles: list = field(default_factory=list)
    groups: list = field(default_factory=list)
    permissions: list = field(default_factory=list)


@dataclass
class PaginatedUsersDTO:
    total: int = 0
    page: int = 1
    page_size: int = 10
    items: list = field(default_factory=list)
