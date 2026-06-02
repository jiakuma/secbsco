# application/dtos.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AgencyDTO:
    id: int
    agency_code: str
    agency_name: str
    agency_type: Optional[str] = None
    agency_level: Optional[str] = None
    parent_agency_id: Optional[int] = None
    parent_agency_name: Optional[str] = None
    region_code: Optional[str] = None
    region_name: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str = "active"
    description: Optional[str] = None
    created_at: Optional[datetime] = None   # 保持 datetime
    updated_at: Optional[datetime] = None   # 保持 datetime
    summary: dict = field(default_factory=dict)


@dataclass
class AgencyTreeDTO:
    id: int
    label: str
    agency_code: str
    agency_name: str
    agency_level: Optional[str] = None
    agency_type: Optional[str] = None
    parent_agency_id: Optional[int] = None
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