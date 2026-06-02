from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success
from .persistence import (
    SQLAlchemyChainRecordRepository, BridgeRelatedTaskPort,
    BridgeTaskResultLookupPort, BridgeAuditLogLookupPort,
    build_record_info, build_result_info, build_log_info,
)
from ..application.use_cases import ListChainRecordsUseCase, GetChainRecordUseCase


router = APIRouter(tags=["链上存证管理"])


def _build_record_info_with_related_task(db: Session, record, related_port: BridgeRelatedTaskPort) -> dict:
    data = build_record_info(record)
    related_task = related_port.build_related_task(record.biz_type, record.biz_id)
    related_dict = asdict(related_task) if related_task else None
    data["related_task"] = related_dict
    data["related_task_id"] = related_task.task_id if related_task else None
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
    repo = SQLAlchemyChainRecordRepository(db)
    related_port = BridgeRelatedTaskPort(db)
    result_lookup = BridgeTaskResultLookupPort(db)
    result = result_lookup.get_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    result_content = build_result_info(result)
    record = repo.mock_anchor_content(biz_type="task_result", biz_id=str(result_id), content=result_content)
    return success(_build_record_info_with_related_task(db, record, related_port))


@router.post("/api/audit-logs/{log_id}/chain-anchor")
def anchor_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo = SQLAlchemyChainRecordRepository(db)
    related_port = BridgeRelatedTaskPort(db)
    log_lookup = BridgeAuditLogLookupPort(db)
    log = log_lookup.get_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="审计日志不存在")
    log_content = build_log_info(log)
    record = repo.mock_anchor_content(biz_type="audit_log", biz_id=str(log_id), content=log_content)
    return success(_build_record_info_with_related_task(db, record, related_port))
