from pydantic import BaseModel
from typing import Optional


class StatTemplateCreate(BaseModel):
    template_code: str
    template_name: str
    stat_type: Optional[str] = None
    metrics_json: Optional[dict] = None
    params_schema_json: Optional[dict] = None
    status: Optional[str] = "enabled"
    description: Optional[str] = None


class StatTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    stat_type: Optional[str] = None
    metrics_json: Optional[dict] = None
    params_schema_json: Optional[dict] = None
    description: Optional[str] = None
