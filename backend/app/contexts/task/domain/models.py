from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TaskInfo:
    id: int | None = None
    task_code: str = ""
    task_name: str = ""
    creator_user_id: int | None = None
    creator_agency_id: int | None = None
    template_id: int | None = None
    stat_start_time: datetime | None = None
    stat_end_time: datetime | None = None
    params_json: dict | None = None
    status: str = "created"
    description: str | None = None
    group_id: int | None = None
    lead_agency_id: int | None = None
    execution_mode: str | None = None
    selected_node_json: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class TaskPartyInfo:
    id: int | None = None
    task_id: int | None = None
    agency_id: int | None = None
    node_id: int | None = None
    dataset_id: int | None = None
    party_role: str = "participant"
    field_mapping_json: dict | None = None
    status: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class TaskResultInfo:
    id: int | None = None
    task_id: int | None = None
    result_json: dict | None = None
    metrics_json: dict | None = None
    result_hash: str | None = None
    status: str = "success"
    error_message: str | None = None
    group_id: int | None = None
    agency_id: int | None = None
    task_type: str | None = None
    result_version: int = 1
    anchor_status: str | None = None
    anchor_time: datetime | None = None
    chain_record_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
