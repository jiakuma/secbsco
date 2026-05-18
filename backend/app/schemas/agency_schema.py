"""机构管理 Schema。"""
from pydantic import BaseModel, Field


class AgencyCreate(BaseModel):
    agency_code: str = Field(..., max_length=64, description="机构编码")
    agency_name: str = Field(..., max_length=128, description="机构名称")
    agency_type: str | None = Field(default=None, max_length=32, description="机构类型")
    agency_level: str | None = Field(default=None, max_length=32, description="机构层级")
    parent_agency_id: int | None = Field(default=None, description="上级机构ID")
    region_code: str | None = Field(default=None, max_length=64, description="行政区划代码")
    region_name: str | None = Field(default=None, max_length=128, description="行政区划名称")
    contact_person: str | None = Field(default=None, max_length=64, description="联系人")
    contact_phone: str | None = Field(default=None, max_length=64, description="联系电话")
    description: str | None = Field(default=None, description="描述")
    status: str = Field(default="active", max_length=32, description="状态")


class AgencyUpdate(BaseModel):
    agency_name: str | None = Field(default=None, max_length=128, description="机构名称")
    agency_type: str | None = Field(default=None, max_length=32, description="机构类型")
    agency_level: str | None = Field(default=None, max_length=32, description="机构层级")
    parent_agency_id: int | None = Field(default=None, description="上级机构ID")
    region_code: str | None = Field(default=None, max_length=64, description="行政区划代码")
    region_name: str | None = Field(default=None, max_length=128, description="行政区划名称")
    contact_person: str | None = Field(default=None, max_length=64, description="联系人")
    contact_phone: str | None = Field(default=None, max_length=64, description="联系电话")
    description: str | None = Field(default=None, description="描述")
