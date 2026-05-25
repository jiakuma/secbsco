from dataclasses import dataclass, field


@dataclass
class TaskDTO:
    id: int | None = None
    task_code: str = ""
    task_name: str = ""
    creator_user_id: int | None = None
    creator_agency_id: int | None = None
    template_id: int | None = None
    stat_start_time: str | None = None
    stat_end_time: str | None = None
    params_json: dict | None = None
    status: str = "created"
    description: str | None = None
    group_id: int | None = None
    lead_agency_id: int | None = None
    execution_mode: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class PaginatedTasksDTO:
    total: int = 0
    page: int = 1
    page_size: int = 10
    items: list[TaskDTO] = field(default_factory=list)


@dataclass
class TaskResultDTO:
    id: int | None = None
    task_id: int | None = None
    result_json: dict | None = None
    metrics_json: dict | None = None
    result_hash: str | None = None
    status: str = "success"
    error_message: str | None = None
    task_type: str | None = None
    anchor_status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class PaginatedResultsDTO:
    total: int = 0
    page: int = 1
    page_size: int = 10
    items: list[TaskResultDTO] = field(default_factory=list)
