from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.task_schema import (
    TaskCreate,
    TaskUpdate,
    TaskStatusUpdate,
    TaskPartyCreate,
    TaskPartyUpdate,
)
from app.services import task_service
from app.services.task_result_service import TaskResultService
from app.schemas.audit_log_schema import AuditLogCreate
from app.services.audit_log_service import AuditLogService

router = APIRouter(
    prefix="/api/tasks",
    tags=["联合统计任务管理"],
)


def write_task_audit_log(
    db: Session,
    request: Request,
    current_user,
    operation_type: str,
    object_type: str,
    object_id: str | None = None,
    task_id: int | None = None,
    operation_desc: str | None = None,
    request_json: dict | None = None,
    result_json: dict | None = None,
):
    """
    写入任务相关审计日志。
    """
    ip_address = None
    if request.client:
        ip_address = request.client.host

    operator_user_id = getattr(current_user, "id", None)
    agency_id = getattr(current_user, "agency_id", None)

    AuditLogService.create_log(
        db=db,
        log_req=AuditLogCreate(
            task_id=task_id,
            agency_id=agency_id,
            operator_user_id=operator_user_id,
            operation_type=operation_type,
            object_type=object_type,
            object_id=object_id,
            operation_desc=operation_desc,
            request_json=request_json,
            result_json=result_json,
            ip_address=ip_address,
        ),
    )


@router.get("")
def list_tasks(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    status: str | None = Query(default=None, description="任务状态"),
    keyword: str | None = Query(default=None, description="任务名称关键词"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.list_tasks(
        db=db,
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
    )
    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.post("")
def create_task(
    task_create: TaskCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    创建任务。

    说明：
    1. creator_user_id 不由前端传入；
    2. 后端从当前登录用户 current_user 中自动写入；
    3. creator_agency_id 如果前端已经选择，则保留前端选择；
       如果前端没传，则尝试使用当前用户所属机构。
    """
    creator_user_id = getattr(current_user, "id", None)
    creator_agency_id = getattr(current_user, "agency_id", None)

    task_create_with_user = task_create.model_copy(
        update={
            "creator_user_id": creator_user_id,
            "creator_agency_id": task_create.creator_agency_id or creator_agency_id,
        }
    )

    data = task_service.create_task(
        db=db,
        task_create=task_create,
        creator_user_id=creator_user_id,
        creator_agency_id=creator_agency_id,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_CREATE",
        object_type="task",
        object_id=str(data.get("id")),
        task_id=data.get("id"),
        operation_desc="创建联合统计任务",
        request_json=task_create_with_user.model_dump(),
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.get("/{task_id}")
def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.get_task_detail(
        db=db,
        task_id=task_id,
    )
    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.put("/{task_id}")
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.update_task(
        db=db,
        task_id=task_id,
        task_update=task_update,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_UPDATE",
        object_type="task",
        object_id=str(task_id),
        task_id=task_id,
        operation_desc="修改联合统计任务",
        request_json=task_update.model_dump(exclude_unset=True),
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.put("/{task_id}/status")
def update_task_status(
    task_id: int,
    status_update: TaskStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.update_task_status(
        db=db,
        task_id=task_id,
        status_update=status_update,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_STATUS_UPDATE",
        object_type="task",
        object_id=str(task_id),
        task_id=task_id,
        operation_desc="更新联合统计任务状态",
        request_json=status_update.model_dump(),
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.get("/{task_id}/parties")
def list_task_parties(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.list_task_parties(db=db, task_id=task_id)
    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.post("/{task_id}/parties")
def create_task_party(
    task_id: int,
    party_create: TaskPartyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.create_task_party(
        db=db,
        task_id=task_id,
        party_create=party_create,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_PARTY_CREATE",
        object_type="task_party",
        object_id=str(data.get("id")),
        task_id=task_id,
        operation_desc="新增任务参与方",
        request_json=party_create.model_dump(),
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.put("/{task_id}/parties/{party_id}")
def update_task_party(
    task_id: int,
    party_id: int,
    party_update: TaskPartyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.update_task_party(
        db=db,
        task_id=task_id,
        party_id=party_id,
        party_update=party_update,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_PARTY_UPDATE",
        object_type="task_party",
        object_id=str(party_id),
        task_id=task_id,
        operation_desc="修改任务参与方",
        request_json=party_update.model_dump(exclude_unset=True),
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.delete("/{task_id}/parties/{party_id}")
def delete_task_party(
    task_id: int,
    party_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.delete_task_party(
        db=db,
        task_id=task_id,
        party_id=party_id,
    )

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_PARTY_DELETE",
        object_type="task_party",
        object_id=str(party_id),
        task_id=task_id,
        operation_desc="删除任务参与方",
        request_json={
            "task_id": task_id,
            "party_id": party_id,
        },
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.post("/{task_id}/run")
def mock_run_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = task_service.mock_run_task(
        db=db,
        task_id=task_id,
    )

    result = TaskResultService.create_or_update_mock_result(
        db=db,
        task_id=task_id,
    )

    data["result"] = TaskResultService.build_result_info(result)
    data["message"] = "Mock 联合统计任务执行成功，已生成统计结果"

    write_task_audit_log(
        db=db,
        request=request,
        current_user=current_user,
        operation_type="TASK_RUN",
        object_type="task",
        object_id=str(task_id),
        task_id=task_id,
        operation_desc="Mock 执行联合统计任务并生成统计结果",
        request_json={
            "task_id": task_id,
        },
        result_json=data,
    )

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }
