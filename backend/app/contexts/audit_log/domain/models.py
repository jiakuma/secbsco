from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AuditLogInfo:
    id: int
    task_id: int | None = None
    agency_id: int | None = None
    operator_user_id: int | None = None
    operation_type: str = ""
    object_type: str | None = None
    object_id: str | None = None
    operation_desc: str | None = None
    request_json: dict | None = None
    result_json: dict | None = None
    ip_address: str | None = None
    created_at: datetime | None = None
