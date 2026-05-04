from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services import task_service
from app.services.audit_log_service import AuditLogService
from app.services.chain_record_service import ChainRecordService
from app.services.task_result_service import TaskResultService


router = APIRouter(
    tags=["链上存证管理"]
)


@router.get("/api/chain-records")
def list_chain_records(
    biz_type: str | None = Query(default=None, description="业务类型"),
    biz_id: str | None = Query(default=None, description="业务ID"),
    status: str | None = Query(default=None, description="存证状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    查询链上存证记录列表
    """
    total, items = ChainRecordService.list_records(
        db=db,
        biz_type=biz_type,
        biz_id=biz_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                ChainRecordService.build_record_info(item)
                for item in items
            ],
        },
    }


@router.get("/api/chain-records/{record_id}")
def get_chain_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    查询链上存证记录详情
    """
    record = ChainRecordService.get_record_by_id(
        db=db,
        record_id=record_id,
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="存证记录不存在",
        )

    return {
        "code": 0,
        "message": "success",
        "data": ChainRecordService.build_record_info(record),
    }


@router.post("/api/tasks/{task_id}/chain-anchor")
def anchor_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    对任务进行 Mock 链上存证
    """
    task = task_service.get_task_or_404(
        db=db,
        task_id=task_id,
    )

    task_content = task_service.task_to_dict(task)

    record = ChainRecordService.mock_anchor_content(
        db=db,
        biz_type="task",
        biz_id=str(task_id),
        content=task_content,
    )

    return {
        "code": 0,
        "message": "success",
        "data": ChainRecordService.build_record_info(record),
    }


@router.post("/api/task-results/{result_id}/chain-anchor")
def anchor_task_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    对任务结果进行 Mock 链上存证
    """
    result = TaskResultService.get_result_by_id(
        db=db,
        result_id=result_id,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="任务结果不存在",
        )

    result_content = TaskResultService.build_result_info(result)

    record = ChainRecordService.mock_anchor_content(
        db=db,
        biz_type="task_result",
        biz_id=str(result_id),
        content=result_content,
    )

    return {
        "code": 0,
        "message": "success",
        "data": ChainRecordService.build_record_info(record),
    }


@router.post("/api/audit-logs/{log_id}/chain-anchor")
def anchor_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    对审计日志进行 Mock 链上存证
    """
    log = AuditLogService.get_log_by_id(
        db=db,
        log_id=log_id,
    )

    if not log:
        raise HTTPException(
            status_code=404,
            detail="审计日志不存在",
        )

    log_content = AuditLogService.build_log_info(log)

    record = ChainRecordService.mock_anchor_content(
        db=db,
        biz_type="audit_log",
        biz_id=str(log_id),
        content=log_content,
    )

    return {
        "code": 0,
        "message": "success",
        "data": ChainRecordService.build_record_info(record),
    }
