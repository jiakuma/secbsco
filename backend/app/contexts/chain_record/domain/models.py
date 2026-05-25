from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ChainRecordInfo:
    id: int
    biz_type: str = ""
    biz_id: str = ""
    content_hash: str = ""
    chain_type: str = "fisco_bcos"
    tx_hash: str | None = None
    block_number: int | None = None
    contract_address: str | None = None
    status: str = "success"
    error_message: str | None = None
    created_at: datetime | None = None
    anchor_id: str | None = None
    group_id: int | None = None
    agency_id: int | None = None
    task_id: int | None = None
    result_id: int | None = None
    dataset_id: int | None = None
    contract_name: str | None = None
    contract_version: str | None = None
    verify_status: str | None = None
    last_verify_time: datetime | None = None
    verify_detail_json: dict | None = None
    updated_at: datetime | None = None


@dataclass
class RelatedTaskInfo:
    task_id: int | None = None
    task_code: str | None = None
    task_name: str | None = None
    task_status: str | None = None
