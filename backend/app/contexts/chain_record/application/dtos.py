from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ChainRecordDTO:
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
    related_task: dict | None = None
    related_task_id: int | None = None


@dataclass
class ChainRecordPageDTO:
    total: int
    page: int
    page_size: int
    items: list[ChainRecordDTO]
