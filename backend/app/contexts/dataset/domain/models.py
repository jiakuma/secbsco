from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DatasetInfo:
    id: int | None = None
    agency_id: int | None = None
    node_id: int | None = None
    dataset_code: str = ""
    dataset_name: str = ""
    data_type: str | None = None
    data_location: str | None = None
    dataset_type: str | None = None
    storage_uri: str | None = None
    schema_json: dict | None = None
    template_id: int | None = None
    status: str = "enabled"
    version: int = 1
    created_by: int | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
