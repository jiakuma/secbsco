from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.task import Task as TaskORM
from app.models.task_party import TaskParty as TaskPartyORM
from app.models.task_result import TaskResult as TaskResultORM
from ..domain.models import TaskInfo, TaskPartyInfo, TaskResultInfo
from ..domain.ports import TaskRepository, TaskPartyRepository, TaskResultRepository, AccessControlPort, AuditLogPort


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _task_to_domain(orm: TaskORM) -> TaskInfo:
    return TaskInfo(
        id=orm.id, task_code=orm.task_code, task_name=orm.task_name,
        creator_user_id=orm.creator_user_id, creator_agency_id=orm.creator_agency_id,
        template_id=orm.template_id, stat_start_time=orm.stat_start_time, stat_end_time=orm.stat_end_time,
        params_json=orm.params_json, status=orm.status, description=orm.description,
        group_id=orm.group_id, lead_agency_id=orm.lead_agency_id,
        execution_mode=orm.execution_mode, selected_node_json=orm.selected_node_json,
        created_at=orm.created_at, updated_at=orm.updated_at,
    )


def _party_to_domain(orm: TaskPartyORM) -> TaskPartyInfo:
    return TaskPartyInfo(
        id=orm.id, task_id=orm.task_id, agency_id=orm.agency_id,
        node_id=orm.node_id, dataset_id=orm.dataset_id,
        party_role=orm.party_role, field_mapping_json=orm.field_mapping_json,
        status=orm.status, error_message=orm.error_message,
        created_at=orm.created_at, updated_at=orm.updated_at,
    )


def _result_to_domain(orm: TaskResultORM) -> TaskResultInfo:
    return TaskResultInfo(
        id=orm.id, task_id=orm.task_id, result_json=orm.result_json,
        metrics_json=orm.metrics_json, result_hash=orm.result_hash,
        status=orm.status, error_message=orm.error_message,
        group_id=orm.group_id, agency_id=orm.agency_id,
        task_type=orm.task_type, result_version=orm.result_version,
        anchor_status=orm.anchor_status, anchor_time=orm.anchor_time,
        chain_record_id=orm.chain_record_id,
        created_at=orm.created_at, updated_at=orm.updated_at,
    )


class SQLAlchemyTaskRepository(TaskRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, task_id: int) -> TaskInfo | None:
        orm = self._db.query(TaskORM).filter(TaskORM.id == task_id).first()
        return _task_to_domain(orm) if orm else None

    def list_tasks(self, *, accessible_group_ids=None, keyword=None, status=None, group_id=None, page=1, page_size=10) -> tuple[list[TaskInfo], int]:
        query = self._db.query(TaskORM)
        if accessible_group_ids is not None:
            query = query.filter(TaskORM.group_id.in_(accessible_group_ids))
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(TaskORM.task_code.like(like), TaskORM.task_name.like(like)))
        if status:
            query = query.filter(TaskORM.status == status)
        if group_id:
            query = query.filter(TaskORM.group_id == group_id)
        total = query.count()
        items = query.order_by(TaskORM.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return [_task_to_domain(i) for i in items], total

    def save(self, task: TaskInfo) -> TaskInfo:
        if task.id is not None:
            orm = self._db.query(TaskORM).filter(TaskORM.id == task.id).first()
            if orm:
                for attr in ["task_name", "template_id", "stat_start_time", "stat_end_time",
                             "params_json", "status", "description", "group_id", "lead_agency_id",
                             "execution_mode", "selected_node_json"]:
                    setattr(orm, attr, getattr(task, attr))
                orm.updated_at = datetime.now()
                self._db.flush()
                self._db.refresh(orm)
                return _task_to_domain(orm)
        orm = TaskORM(
            task_code=task.task_code, task_name=task.task_name,
            creator_user_id=task.creator_user_id, creator_agency_id=task.creator_agency_id,
            template_id=task.template_id, status=task.status, description=task.description,
            group_id=task.group_id, lead_agency_id=task.lead_agency_id,
            execution_mode=task.execution_mode,
        )
        self._db.add(orm)
        self._db.flush()
        self._db.refresh(orm)
        return _task_to_domain(orm)

    def delete(self, task_id: int) -> None:
        t = self._db.query(TaskORM).filter(TaskORM.id == task_id).first()
        if t:
            self._db.delete(t)
            self._db.flush()


class SQLAlchemyTaskPartyRepository(TaskPartyRepository):
    def __init__(self, db: Session):
        self._db = db

    def list_parties(self, task_id: int) -> list[TaskPartyInfo]:
        orms = self._db.query(TaskPartyORM).filter(TaskPartyORM.task_id == task_id).order_by(TaskPartyORM.id.asc()).all()
        return [_party_to_domain(o) for o in orms]

    def save_party(self, party: TaskPartyInfo) -> TaskPartyInfo:
        if party.id is not None:
            orm = self._db.query(TaskPartyORM).filter(TaskPartyORM.id == party.id).first()
            if orm:
                for attr in ["agency_id", "node_id", "dataset_id", "party_role",
                             "field_mapping_json", "status", "error_message"]:
                    setattr(orm, attr, getattr(party, attr))
                orm.updated_at = datetime.now()
                self._db.flush()
                return _party_to_domain(orm)
        orm = TaskPartyORM(
            task_id=party.task_id, agency_id=party.agency_id, node_id=party.node_id,
            dataset_id=party.dataset_id, party_role=party.party_role,
            field_mapping_json=party.field_mapping_json, status=party.status,
            error_message=party.error_message,
        )
        self._db.add(orm)
        self._db.flush()
        return _party_to_domain(orm)

    def delete_party(self, party_id: int) -> None:
        p = self._db.query(TaskPartyORM).filter(TaskPartyORM.id == party_id).first()
        if p:
            self._db.delete(p)
            self._db.flush()


class SQLAlchemyTaskResultRepository(TaskResultRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_task_id(self, task_id: int) -> TaskResultInfo | None:
        orm = self._db.query(TaskResultORM).filter(TaskResultORM.task_id == task_id).first()
        return _result_to_domain(orm) if orm else None

    def get_by_id(self, result_id: int) -> TaskResultInfo | None:
        orm = self._db.query(TaskResultORM).filter(TaskResultORM.id == result_id).first()
        return _result_to_domain(orm) if orm else None

    def list_results(self, *, task_id=None, status=None, page=1, page_size=10) -> tuple[list[TaskResultInfo], int]:
        query = self._db.query(TaskResultORM)
        if task_id:
            query = query.filter(TaskResultORM.task_id == task_id)
        if status:
            query = query.filter(TaskResultORM.status == status)
        total = query.count()
        items = query.order_by(TaskResultORM.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return [_result_to_domain(i) for i in items], total


class BridgeAccessControlPort(AccessControlPort):
    def __init__(self, db: Session):
        self._db = db

    def get_accessible_group_ids(self, user_id: int) -> list[int] | None:
        from app.contexts.shared.access_control_service import get_accessible_group_ids
        return get_accessible_group_ids(self._db, user_id)

    def check_task_access(self, current_user, task_id: int) -> None:
        from app.contexts.shared.access_control_service import check_group_access
        from app.models.task import Task as TaskORM
        task = self._db.query(TaskORM).filter(TaskORM.id == task_id).first()
        if not task or not task.group_id:
            return
        check_group_access(self._db, current_user.id, task.group_id)

    def check_task_run_access(self, current_user, task_id: int) -> None:
        from app.contexts.shared.access_control_service import check_task_run_access
        check_task_run_access(self._db, current_user, task_id)


class BridgeAuditLogPort(AuditLogPort):
    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type=None, resource_id=None, agency_id=None, group_id=None, request=None) -> None:
        from app.contexts.shared.access_control_service import write_operate_log
        write_operate_log(db=db, user_id=user_id, username=username, operation_type=operation_type,
                          resource_type=resource_type, resource_id=resource_id,
                          agency_id=agency_id, group_id=group_id, request=request)
