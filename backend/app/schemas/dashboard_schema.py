from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DashboardSummaryData(BaseModel):
    agency_count: int
    node_count: int
    dataset_count: int
    stat_template_count: int
    task_count: int
    success_task_count: int
    result_count: int
    audit_log_count: int
    chain_record_count: int


class RecentTaskItem(BaseModel):
    id: int
    task_code: str | None = None
    task_name: str | None = None
    creator_user_id: int | None = None
    creator_agency_id: int | None = None
    template_id: int | None = None
    stat_start_time: datetime | None = None
    stat_end_time: datetime | None = None
    status: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RecentResultItem(BaseModel):
    id: int
    task_id: int
    result_json: Any | None = None
    metrics_json: Any | None = None
    result_hash: str | None = None
    status: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RecentAuditLogItem(BaseModel):
    id: int
    task_id: int | None = None
    agency_id: int | None = None
    operator_user_id: int | None = None
    operation_type: str | None = None
    object_type: str | None = None
    object_id: str | None = None
    operation_desc: str | None = None
    request_json: Any | None = None
    result_json: Any | None = None
    ip_address: str | None = None
    created_at: datetime | None = None


class RecentChainRecordItem(BaseModel):
    id: int
    biz_type: str
    biz_id: str
    content_hash: str | None = None
    chain_type: str | None = None
    tx_hash: str | None = None
    block_number: int | None = None
    contract_address: str | None = None
    status: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None


class DashboardSummaryResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: DashboardSummaryData


class RecentTasksResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: list[RecentTaskItem]


class RecentResultsResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: list[RecentResultItem]


class RecentAuditLogsResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: list[RecentAuditLogItem]


class RecentChainRecordsResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: list[RecentChainRecordItem]