from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    task_code: str = Field(..., max_length=64, description="任务编码")
    task_name: str = Field(..., max_length=128, description="任务名称")

    creator_user_id: int | None = Field(default=None, description="创建用户ID")
    creator_agency_id: int | None = Field(default=None, description="创建机构ID")
    template_id: int | None = Field(default=None, description="统计模板ID")
    group_id: int | None = Field(default=None, description="所属群组ID")
    task_type: str | None = Field(default=None, max_length=32, description="任务类型")

    stat_start_time: datetime | None = Field(default=None, description="统计开始时间")
    stat_end_time: datetime | None = Field(default=None, description="统计结束时间")
    params_json: dict[str, Any] | None = Field(default=None, description="任务参数")

    status: str = Field(default="created", max_length=32, description="任务状态")
    description: str | None = Field(default=None, description="描述")


class TaskUpdate(BaseModel):
    task_name: str | None = Field(default=None, max_length=128, description="任务名称")
    template_id: int | None = Field(default=None, description="统计模板ID")

    stat_start_time: datetime | None = Field(default=None, description="统计开始时间")
    stat_end_time: datetime | None = Field(default=None, description="统计结束时间")
    params_json: dict[str, Any] | None = Field(default=None, description="任务参数")

    description: str | None = Field(default=None, description="描述")


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., max_length=32, description="任务状态")


class TaskResponse(BaseModel):
    id: int
    task_code: str
    task_name: str

    creator_user_id: int | None = None
    creator_agency_id: int | None = None
    template_id: int | None = None

    stat_start_time: datetime | None = None
    stat_end_time: datetime | None = None
    params_json: dict[str, Any] | None = None

    status: str
    description: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskPartyCreate(BaseModel):
    agency_id: int = Field(..., description="参与机构ID")
    node_id: int | None = Field(default=None, description="执行节点ID")
    dataset_id: int | None = Field(default=None, description="数据集ID")
    data_resource_name: str | None = Field(default=None, description="数据资源名称")

    party_role: str | None = Field(default=None, max_length=64, description="参与方角色")
    field_mapping_json: dict[str, Any] | None = Field(default=None, description="字段映射")

    status: str = Field(default="pending", max_length=32, description="参与方状态")
    error_message: str | None = Field(default=None, description="错误信息")


class TaskPartyUpdate(BaseModel):
    agency_id: int | None = Field(default=None, description="参与机构ID")
    node_id: int | None = Field(default=None, description="执行节点ID")
    dataset_id: int | None = Field(default=None, description="数据集ID")

    party_role: str | None = Field(default=None, max_length=64, description="参与方角色")
    field_mapping_json: dict[str, Any] | None = Field(default=None, description="字段映射")

    status: str | None = Field(default=None, max_length=32, description="参与方状态")
    error_message: str | None = Field(default=None, description="错误信息")


class TaskPartyResponse(BaseModel):
    id: int
    task_id: int
    agency_id: int
    node_id: int | None = None
    dataset_id: int | None = None

    party_role: str | None = None
    field_mapping_json: dict[str, Any] | None = None
    status: str
    error_message: str | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)