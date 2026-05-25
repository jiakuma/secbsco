from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskCreate(BaseModel):
    task_code: str
    task_name: str
    creator_user_id: Optional[int] = None
    creator_agency_id: Optional[int] = None
    template_id: Optional[int] = None
    group_id: Optional[int] = None
    task_type: Optional[str] = None
    stat_start_time: Optional[datetime] = None
    stat_end_time: Optional[datetime] = None
    params_json: Optional[dict] = None
    status: Optional[str] = "created"
    description: Optional[str] = None


class TaskUpdate(BaseModel):
    task_name: Optional[str] = None
    template_id: Optional[int] = None
    stat_start_time: Optional[datetime] = None
    stat_end_time: Optional[datetime] = None
    params_json: Optional[dict] = None
    description: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    status: str


class TaskPartyCreate(BaseModel):
    agency_id: Optional[int] = None
    node_id: Optional[int] = None
    dataset_id: Optional[int] = None
    data_resource_name: Optional[str] = None
    party_role: Optional[str] = None
    field_mapping_json: Optional[dict] = None
    status: Optional[str] = None
    error_message: Optional[str] = None


class TaskPartyUpdate(BaseModel):
    agency_id: Optional[int] = None
    node_id: Optional[int] = None
    dataset_id: Optional[int] = None
    party_role: Optional[str] = None
    field_mapping_json: Optional[dict] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
