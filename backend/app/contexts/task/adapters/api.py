from dataclasses import asdict
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success, fail
from .persistence import (
    SQLAlchemyTaskRepository, SQLAlchemyTaskPartyRepository, SQLAlchemyTaskResultRepository,
    BridgeAccessControlPort, BridgeAuditLogPort,
)
from .schemas import TaskCreate, TaskUpdate, TaskStatusUpdate, TaskPartyCreate, TaskPartyUpdate
from ..application.use_cases import ListTasksUseCase, GetTaskDetailUseCase, ListTaskResultsUseCase, GetTaskResultUseCase


router = APIRouter(prefix="/api/tasks", tags=["联合统计任务管理"])


def _dto_to_dict(dto) -> dict:
    return asdict(dto)


@router.get("")
def list_tasks(
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    group_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo = SQLAlchemyTaskRepository(db)
    access_control = BridgeAccessControlPort(db)
    uc = ListTasksUseCase(repo, access_control)
    result = uc.execute(current_user, keyword=keyword, status=status, group_id=group_id, page=page, page_size=page_size)
    return success(_dto_to_dict(result))


@router.post("")
def create_task(
    payload: TaskCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_service import create_task as _create
    data = payload.model_dump(exclude_unset=True)
    data["creator_user_id"] = current_user.id
    data["creator_agency_id"] = current_user.agency_id
    result = _create(db, data, current_user.id, current_user.agency_id)
    db.commit()
    return success(result)


@router.get("/{task_id}")
def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_service import get_task_detail as _detail
    result = _detail(db, task_id)
    return success(result)


@router.put("/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_service import update_task as _update
    result = _update(db, task_id, payload)
    db.commit()
    return success(result)


@router.put("/{task_id}/status")
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_service import update_task_status as _update
    result = _update(db, task_id, payload)
    db.commit()
    return success(result)


@router.get("/{task_id}/parties")
def list_task_parties(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_service import list_task_parties as _list
    result = _list(db, task_id)
    return success(result)


@router.post("/{task_id}/parties")
def create_task_party(
    task_id: int,
    payload: TaskPartyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.api.task_api import create_task_party as _old_create
    result = _old_create(task_id, payload, request, db, current_user)
    return result


@router.put("/{task_id}/parties/{party_id}")
def update_task_party(
    task_id: int,
    party_id: int,
    payload: TaskPartyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_service import update_task_party as _update
    result = _update(db, task_id, party_id, payload)
    db.commit()
    return success(result)


@router.delete("/{task_id}/parties/{party_id}")
def delete_task_party(
    task_id: int,
    party_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_service import delete_task_party as _delete
    result = _delete(db, task_id, party_id)
    db.commit()
    return success(result)


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.api.task_api import delete_task as _old_delete
    return _old_delete(task_id, request, db, current_user)


@router.post("/{task_id}/chain-anchor")
def anchor_task_result(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.api.task_api import anchor_task_result as _old_anchor
    return _old_anchor(task_id, request, db, current_user)


@router.post("/{task_id}/run")
def run_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.api.task_api import run_task as _old_run
    return _old_run(task_id, request, db, current_user)


@router.get("/{task_id}/result")
def get_result_by_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_service import get_task_or_404
    from app.services.task_result_service import TaskResultService
    from fastapi import HTTPException
    get_task_or_404(db, task_id)
    result = TaskResultService.get_result_by_task_id(db, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="该任务暂无统计结果")
    return success(TaskResultService.build_result_info(result))


result_router = APIRouter(prefix="/api/task-results", tags=["联合统计结果管理"])


@result_router.get("")
def list_task_results(
    task_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_result_service import TaskResultService
    total, items = TaskResultService.list_results(db, task_id=task_id, status=status, page=page, page_size=page_size)
    return success({
        "total": total, "page": page, "page_size": page_size,
        "items": [TaskResultService.build_result_info(i) for i in items],
    })


@result_router.get("/{result_id}")
def get_task_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_result_service import TaskResultService
    result = TaskResultService.get_result_by_id(db, result_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="任务结果不存在")
    return success(TaskResultService.build_result_info(result))
