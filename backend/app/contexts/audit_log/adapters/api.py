from dataclasses import asdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success
from .persistence import SQLAlchemyAuditLogRepository
from ..application.use_cases import ListAuditLogsUseCase, GetAuditLogUseCase


router = APIRouter(prefix="/api/audit-logs", tags=["审计日志管理"])


@router.get("")
def list_audit_logs(
    task_id: int | None = Query(default=None),
    agency_id: int | None = Query(default=None),
    operator_user_id: int | None = Query(default=None),
    operation_type: str | None = Query(default=None),
    object_type: str | None = Query(default=None),
    object_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo = SQLAlchemyAuditLogRepository(db)
    uc = ListAuditLogsUseCase(repo)
    result = uc.execute(
        task_id=task_id,
        agency_id=agency_id,
        operator_user_id=operator_user_id,
        operation_type=operation_type,
        object_type=object_type,
        object_id=object_id,
        page=page,
        page_size=page_size,
    )
    return success(asdict(result))


@router.get("/{log_id}")
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo = SQLAlchemyAuditLogRepository(db)
    uc = GetAuditLogUseCase(repo)
    result = uc.execute(log_id)
    return success(asdict(result))
