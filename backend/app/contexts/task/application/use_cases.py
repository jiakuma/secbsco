from ..domain.models import TaskInfo, TaskResultInfo
from ..domain.ports import TaskRepository, TaskPartyRepository, TaskResultRepository, AccessControlPort, AuditLogPort
from ..domain.exceptions import TaskNotFound, TaskResultNotFound
from .dtos import TaskDTO, PaginatedTasksDTO, TaskResultDTO, PaginatedResultsDTO


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _to_task_dto(t: TaskInfo) -> TaskDTO:
    return TaskDTO(
        id=t.id, task_code=t.task_code, task_name=t.task_name,
        creator_user_id=t.creator_user_id, creator_agency_id=t.creator_agency_id,
        template_id=t.template_id,
        stat_start_time=_format_dt(t.stat_start_time), stat_end_time=_format_dt(t.stat_end_time),
        params_json=t.params_json, status=t.status, description=t.description,
        group_id=t.group_id, lead_agency_id=t.lead_agency_id, execution_mode=t.execution_mode,
        created_at=_format_dt(t.created_at), updated_at=_format_dt(t.updated_at),
    )


def _to_result_dto(r: TaskResultInfo) -> TaskResultDTO:
    return TaskResultDTO(
        id=r.id, task_id=r.task_id, result_json=r.result_json,
        metrics_json=r.metrics_json, result_hash=r.result_hash,
        status=r.status, error_message=r.error_message,
        task_type=r.task_type, anchor_status=r.anchor_status,
        created_at=_format_dt(r.created_at), updated_at=_format_dt(r.updated_at),
    )


class ListTasksUseCase:
    def __init__(self, repo: TaskRepository, access_control: AccessControlPort):
        self._repo = repo
        self._access_control = access_control

    def execute(self, current_user, **filters) -> PaginatedTasksDTO:
        accessible_ids = self._access_control.get_accessible_group_ids(current_user.id)
        tasks, total = self._repo.list_tasks(accessible_group_ids=accessible_ids, **filters)
        items = [_to_task_dto(t) for t in tasks]
        return PaginatedTasksDTO(total=total, page=filters.get("page", 1), page_size=filters.get("page_size", 10), items=items)


class GetTaskDetailUseCase:
    def __init__(self, repo: TaskRepository, access_control: AccessControlPort):
        self._repo = repo
        self._access_control = access_control

    def execute(self, task_id: int, current_user) -> TaskDTO:
        self._access_control.check_task_access(current_user, task_id)
        t = self._repo.get_by_id(task_id)
        if not t:
            raise TaskNotFound()
        return _to_task_dto(t)


class ListTaskResultsUseCase:
    def __init__(self, result_repo: TaskResultRepository):
        self._result_repo = result_repo

    def execute(self, **filters) -> PaginatedResultsDTO:
        results, total = self._result_repo.list_results(**filters)
        items = [_to_result_dto(r) for r in results]
        return PaginatedResultsDTO(total=total, page=filters.get("page", 1), page_size=filters.get("page_size", 10), items=items)


class GetTaskResultUseCase:
    def __init__(self, result_repo: TaskResultRepository):
        self._result_repo = result_repo

    def execute_by_id(self, result_id: int) -> TaskResultDTO:
        r = self._result_repo.get_by_id(result_id)
        if not r:
            raise TaskResultNotFound()
        return _to_result_dto(r)

    def execute_by_task_id(self, task_id: int) -> TaskResultDTO:
        r = self._result_repo.get_by_task_id(task_id)
        if not r:
            raise TaskResultNotFound()
        return _to_result_dto(r)
