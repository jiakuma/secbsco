from dataclasses import dataclass, field


@dataclass
class GroupDTO:
    id: int | None = None
    group_code: str = ""
    group_name: str = ""
    group_level: str | None = None
    region_code: str | None = None
    region_name: str | None = None
    lead_agency_id: int | None = None
    lead_agency_name: str | None = None
    description: str | None = None
    status: str = "draft"
    approval_required: bool = False
    approval_status: str = "none"
    member_count: int = 0
    user_count: int = 0
    node_count: int = 0
    task_count: int = 0
    can_delete: bool = False
    need_delete_approval: bool = False
    can_approve_delete: bool = False
    created_by: int | None = None
    creator_agency_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class PaginatedGroupsDTO:
    total: int = 0
    page: int = 1
    page_size: int = 10
    items: list[GroupDTO] = field(default_factory=list)


@dataclass
class GroupMemberDTO:
    id: int | None = None
    group_id: int | None = None
    agency_id: int | None = None
    agency_name: str | None = None
    member_role: str = "participant"
    is_lead: bool = False
    join_status: str = "active"
    joined_at: str | None = None
    created_at: str | None = None


@dataclass
class GroupNodeDTO:
    id: int | None = None
    group_id: int | None = None
    agency_id: int | None = None
    agency_name: str | None = None
    node_id: int | None = None
    node_name: str | None = None
    node_type: str | None = None
    node_usage_role: str = "group_service"
    auth_status: str = "active"
    priority_level: int = 1
    max_concurrent_tasks: int = 1
    authorized_at: str | None = None
    created_at: str | None = None


@dataclass
class GroupDatasetDTO:
    id: int | None = None
    group_id: int | None = None
    agency_id: int | None = None
    agency_name: str | None = None
    dataset_id: int | None = None
    dataset_name: str | None = None
    dataset_code: str | None = None
    auth_status: str = "active"
    authorized_at: str | None = None
    created_at: str | None = None


@dataclass
class GroupTemplateDTO:
    id: int | None = None
    group_id: int | None = None
    agency_id: int | None = None
    agency_name: str | None = None
    template_id: int | None = None
    template_name: str | None = None
    template_code: str | None = None
    auth_status: str = "active"
    authorized_at: str | None = None
    created_at: str | None = None
