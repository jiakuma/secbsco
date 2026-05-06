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


def _safe_int(value) -> int | None:
    """
    将 biz_id 等字符串安全转换为整数。
    """
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_related_task_info(db: Session, record) -> dict | None:
    """
    根据 chain_record.biz_type / biz_id 推导关联任务。

    说明：
    1. biz_type = task 时，biz_id 本身就是 task.id；
    2. biz_type = task_result 时，biz_id 是 task_result.id，需要反查 task_result.task_id；
    3. biz_type = audit_log 时，biz_id 是 audit_log.id，需要反查 audit_log.task_id；
    4. 当前阶段不修改 chain_record 表结构，只在接口返回层补充 related_task 信息。
    """
    biz_type = getattr(record, "biz_type", None)
    biz_id = _safe_int(getattr(record, "biz_id", None))

    if not biz_type or biz_id is None:
        return None

    task_id: int | None = None

    if biz_type == "task":
        task_id = biz_id

    elif biz_type == "task_result":
        result = TaskResultService.get_result_by_id(
            db=db,
            result_id=biz_id,
        )
        task_id = getattr(result, "task_id", None) if result else None

    elif biz_type == "audit_log":
        log = AuditLogService.get_log_by_id(
            db=db,
            log_id=biz_id,
        )
        task_id = getattr(log, "task_id", None) if log else None

    if not task_id:
        return None

    try:
        task = task_service.get_task_or_404(
            db=db,
            task_id=task_id,
        )
    except Exception:
        return {
            "task_id": task_id,
            "task_code": None,
            "task_name": None,
            "task_status": None,
        }

    return {
        "task_id": getattr(task, "id", task_id),
        "task_code": getattr(task, "task_code", None),
        "task_name": getattr(task, "task_name", None),
        "task_status": getattr(task, "status", None),
    }


def _build_record_info_with_related_task(db: Session, record) -> dict:
    """
    构造存证记录返回对象，并补充前端跳转任务详情所需字段。
    """
    data = ChainRecordService.build_record_info(record)
    related_task = _build_related_task_info(db=db, record=record)

    data["related_task"] = related_task
    data["related_task_id"] = related_task.get("task_id") if related_task else None

    return data


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
                _build_record_info_with_related_task(db=db, record=item)
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
        "data": _build_record_info_with_related_task(db=db, record=record),
    }


# @router.post("/api/tasks/{task_id}/chain-anchor")
# def anchor_task(
#     task_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user),
# ):
#     """
#     对任务进行 Mock 链上存证
#     """
#     task = task_service.get_task_or_404(
#         db=db,
#         task_id=task_id,
#     )
#
#     task_content = task_service.task_to_dict(task)
#
#     record = ChainRecordService.mock_anchor_content(
#         db=db,
#         biz_type="task",
#         biz_id=str(task_id),
#         content=task_content,
#     )
#
#     return {
#         "code": 0,
#         "message": "success",
#         "data": ChainRecordService.build_record_info(record),
#     }


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
        "data": _build_record_info_with_related_task(db=db, record=record),
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
        "data": _build_record_info_with_related_task(db=db, record=record),
    }
