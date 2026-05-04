from typing import Optional

from pydantic import BaseModel


class TaskResultCreate(BaseModel):
    task_id: int
    result_json: Optional[dict] = None
    metrics_json: Optional[dict] = None
    result_hash: Optional[str] = None
    status: Optional[str] = "success"
    error_message: Optional[str] = None


class TaskResultUpdate(BaseModel):
    result_json: Optional[dict] = None
    metrics_json: Optional[dict] = None
    result_hash: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None