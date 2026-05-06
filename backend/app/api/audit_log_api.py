from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.audit_log_service import AuditLogService


router = APIRouter(
    prefix="/api/audit-logs",
    tags=["审计日志管理"]
)


@router.get("")
def list_audit_logs(
    task_id: int | None = Query(default=None, description="任务ID"),
    agency_id: int | None = Query(default=None, description="机构ID"),
    operator_user_id: int | None = Query(default=None, description="操作用户ID"),
    operation_type: str | None = Query(default=None, description="操作类型"),
    object_type: str | None = Query(default=None, description="对象类型"),
    object_id: str | None = Query(default=None, description="对象ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    查询审计日志列表。

    第十七阶段补充 object_id 查询条件，用于：
    - 存证记录 -> 审计日志联动；
    - object_type = chain_record；
    - object_id = chain_record.id。
    """
    total, items = AuditLogService.list_logs(
        db=db,
        task_id=task_id,
        agency_id=agency_id,
        operator_user_id=operator_user_id,
        operation_type=operation_type,
        object_type=object_type,
        object_id=object_id,
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
                AuditLogService.build_log_info(item)
                for item in items
            ],
        },
    }


@router.get("/{log_id}")
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    查询审计日志详情
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

    return {
        "code": 0,
        "message": "success",
        "data": AuditLogService.build_log_info(log),
    }
