from typing import Optional

from pydantic import BaseModel


class AuditLogCreate(BaseModel):
    task_id: Optional[int] = None
    agency_id: Optional[int] = None
    operator_user_id: Optional[int] = None

    operation_type: str
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    operation_desc: Optional[str] = None
    request_json: Optional[dict] = None
    result_json: Optional[dict] = None
    ip_address: Optional[str] = None