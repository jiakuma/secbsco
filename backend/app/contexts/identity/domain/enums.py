from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GOVERNOR = "governor"


class ScopeType(str, Enum):
    PLATFORM = "platform"
    AGENCY = "agency"
    GROUP = "group"


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"
    ARCHIVED = "archived"


class JoinStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class BindingStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"
