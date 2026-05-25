from pydantic import BaseModel
from typing import Optional


class DatasetCreate(BaseModel):
    agency_id: int
    dataset_code: str
    dataset_name: str
    node_id: Optional[int] = None
    data_type: Optional[str] = None
    data_location: Optional[str] = None
    dataset_type: Optional[str] = None
    storage_uri: Optional[str] = None
    schema_json: Optional[dict] = None
    status: Optional[str] = "enabled"
    description: Optional[str] = None


class DatasetUpdate(BaseModel):
    agency_id: Optional[int] = None
    dataset_name: Optional[str] = None
    node_id: Optional[int] = None
    data_type: Optional[str] = None
    data_location: Optional[str] = None
    dataset_type: Optional[str] = None
    storage_uri: Optional[str] = None
    schema_json: Optional[dict] = None
    description: Optional[str] = None
