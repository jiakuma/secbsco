from enum import Enum


class GroupStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    REJECTED = "rejected"
    DISSOLVING = "dissolving"
    DISSOLVED = "dissolved"
    ARCHIVED = "archived"
    DISABLED = "disabled"


class ApprovalStatus(str, Enum):
    NONE = "none"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GroupLevel(str, Enum):
    COUNTY = "county"
    CITY = "city"
    PROVINCE = "province"
    NATIONAL = "national"


class MemberRole(str, Enum):
    LEAD_AGENCY = "lead_agency"
    PARTICIPANT = "participant"
    DATA_PROVIDER = "data_provider"
    COMPUTE_PROVIDER = "compute_provider"
    OBSERVER = "observer"


class JoinStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REMOVED = "removed"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class NodeUsageRole(str, Enum):
    GROUP_SERVICE = "group_service"
    GROUP_DATA = "group_data"
    GROUP_COMPUTE = "group_compute"
    GROUP_BLOCKCHAIN = "group_blockchain"


class AuthStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"
    ARCHIVED = "archived"
