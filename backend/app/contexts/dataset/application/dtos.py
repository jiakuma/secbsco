from dataclasses import dataclass, field


@dataclass
class DatasetDTO:
    id: int | None = None
    dataset_code: str = ""
    dataset_name: str = ""
    agency_id: int | None = None
    agency_name: str | None = None
    node_id: int | None = None
    node_name: str | None = None
    data_type: str | None = None
    data_location: str | None = None
    storage_uri: str | None = None
    dataset_type: str | None = None
    description: str | None = None
    status: str = "enabled"
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class PaginatedDatasetsDTO:
    total: int = 0
    page: int = 1
    page_size: int = 10
    items: list[DatasetDTO] = field(default_factory=list)
