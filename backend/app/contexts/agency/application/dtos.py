from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgencyDTO:
    id: int
    agency_code: str
    agency_name: str
    agency_type: str | None = None
    agency_level: str | None = None
    parent_agency_id: int | None = None
    parent_agency_name: str | None = None
    region_code: str | None = None
    region_name: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    status: str = "active"
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    summary: dict = field(default_factory=dict)


@dataclass
class AgencyTreeDTO:
    id: int
    label: str
    agency_code: str
    agency_name: str
    agency_level: str | None = None
    agency_type: str | None = None
    parent_agency_id: int | None = None
    status: str = "active"
    children: list = field(default_factory=list)


@dataclass
class PaginatedAgenciesDTO:
    total: int
    page: int
    page_size: int
    items: list[AgencyDTO] = field(default_factory=list)


@dataclass
class DeleteResultDTO:
    deleted: bool = True
    agency_id: int = 0
    deleted_agency_ids: list[int] = field(default_factory=list)
    deleted_user_count: int = 0
    deleted_node_count: int = 0
