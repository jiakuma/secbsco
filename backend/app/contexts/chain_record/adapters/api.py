from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success
from .persistence import SQLAlchemyChainRecordRepository, BridgeRelatedTaskPort
from ..application.use_cases import ListChainRecordsUseCase, GetChainRecordUseCase


router = APIRouter(tags=["链上存证管理"])


def _build_record_info_with_related_task(db: Session, record) -> dict:
    from app.services.chain_record_service import ChainRecordService
    from app.api.chain_record_api import _build_related_task_info
    data = ChainRecordService.build_record_info(record)
    related_task = _build_related_task_info(db=db, record=record)
    data["related_task"] = related_task
    data["related_task_id"] = related_task.get("task_id") if related_task else None
    return data


@router.get("/api/chain-records")
def list_chain_records(
    biz_type: str | None = Query(default=None),
    biz_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo = SQLAlchemyChainRecordRepository(db)
    related_port = BridgeRelatedTaskPort(db)
    uc = ListChainRecordsUseCase(repo, related_port)
    result = uc.execute(biz_type=biz_type, biz_id=biz_id, status=status, page=page, page_size=page_size)
    return success(asdict(result))


@router.get("/api/chain-records/{record_id}")
def get_chain_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo = SQLAlchemyChainRecordRepository(db)
    related_port = BridgeRelatedTaskPort(db)
    uc = GetChainRecordUseCase(repo, related_port)
    result = uc.execute(record_id)
    return success(asdict(result))


@router.post("/api/task-results/{result_id}/chain-anchor")
def anchor_task_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.task_result_service import TaskResultService
    from app.services.chain_record_service import ChainRecordService
    result = TaskResultService.get_result_by_id(db=db, result_id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    result_content = TaskResultService.build_result_info(result)
    record = ChainRecordService.mock_anchor_content(
        db=db, biz_type="task_result", biz_id=str(result_id), content=result_content,
    )
    return success(_build_record_info_with_related_task(db, record))


@router.post("/api/audit-logs/{log_id}/chain-anchor")
def anchor_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.audit_log_service import AuditLogService
    from app.services.chain_record_service import ChainRecordService
    log = AuditLogService.get_log_by_id(db=db, log_id=log_id)
    if not log:
        raise HTTPException(status_code=404, detail="审计日志不存在")
    log_content = AuditLogService.build_log_info(log)
    record = ChainRecordService.mock_anchor_content(
        db=db, biz_type="audit_log", biz_id=str(log_id), content=log_content,
    )
    return success(_build_record_info_with_related_task(db, record))
