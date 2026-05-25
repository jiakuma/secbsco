from pydantic import BaseModel, Field
from typing import Optional


class GroupCreate(BaseModel):
    group_code: str = Field(..., max_length=64)
    group_name: str = Field(..., max_length=128)
    group_level: str = Field(default="city")
    region_code: Optional[str] = None
    region_name: Optional[str] = None
    lead_agency_id: Optional[int] = None
    member_agency_ids: list[int] = Field(default_factory=list)
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    group_name: Optional[str] = None
    group_level: Optional[str] = None
    region_code: Optional[str] = None
    region_name: Optional[str] = None
    description: Optional[str] = None


class GroupApprove(BaseModel):
    remark: str = Field(default="审批通过")


class GroupReject(BaseModel):
    reason: str = Field(..., min_length=1)


class AddGroupMember(BaseModel):
    agency_id: int
    member_type: str = Field(default="participant")
    remark: str = Field(default="")


class AddGroupUser(BaseModel):
    user_id: int
    role_code: str = Field(default="user")
    remark: str = Field(default="")


class UpdateGroupUserRole(BaseModel):
    role_code: str


class AddGroupNode(BaseModel):
    node_id: int
    remark: str = Field(default="")


class RejectDeleteRequest(BaseModel):
    reason: str = Field(..., min_length=1)
