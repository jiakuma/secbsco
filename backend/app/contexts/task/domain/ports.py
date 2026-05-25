from abc import ABC, abstractmethod
from typing import Any
from .models import TaskInfo, TaskPartyInfo, TaskResultInfo


class TaskRepository(ABC):
    @abstractmethod
    def get_by_id(self, task_id: int) -> TaskInfo | None: ...

    @abstractmethod
    def list_tasks(self, *, accessible_group_ids=None, keyword=None, status=None, group_id=None, page=1, page_size=10) -> tuple[list[TaskInfo], int]: ...

    @abstractmethod
    def save(self, task: TaskInfo) -> TaskInfo: ...

    @abstractmethod
    def delete(self, task_id: int) -> None: ...


class TaskPartyRepository(ABC):
    @abstractmethod
    def list_parties(self, task_id: int) -> list[TaskPartyInfo]: ...

    @abstractmethod
    def save_party(self, party: TaskPartyInfo) -> TaskPartyInfo: ...

    @abstractmethod
    def delete_party(self, party_id: int) -> None: ...


class TaskResultRepository(ABC):
    @abstractmethod
    def get_by_task_id(self, task_id: int) -> TaskResultInfo | None: ...

    @abstractmethod
    def get_by_id(self, result_id: int) -> TaskResultInfo | None: ...

    @abstractmethod
    def list_results(self, *, task_id=None, status=None, page=1, page_size=10) -> tuple[list[TaskResultInfo], int]: ...


class AccessControlPort(ABC):
    @abstractmethod
    def get_accessible_group_ids(self, user_id: int) -> list[int] | None: ...

    @abstractmethod
    def check_task_access(self, current_user, task_id: int) -> None: ...

    @abstractmethod
    def check_task_run_access(self, current_user, task_id: int) -> None: ...


class AuditLogPort(ABC):
    @abstractmethod
    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type=None, resource_id=None, agency_id=None, group_id=None, request=None) -> None: ...
