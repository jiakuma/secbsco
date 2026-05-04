from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services import task_service
from app.services.task_result_service import TaskResultService


router = APIRouter(
    tags=["联合统计结果管理"]
)


@router.get("/api/task-results")
def list_task_results(
    task_id: int | None = Query(default=None, description="任务ID"),
    status: str | None = Query(default=None, description="结果状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    查询联合统计结果列表
    """
    total, items = TaskResultService.list_results(
        db=db,
        task_id=task_id,
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
                TaskResultService.build_result_info(item)
                for item in items
            ],
        },
    }


@router.get("/api/task-results/{result_id}")
def get_task_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    查询联合统计结果详情
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

    return {
        "code": 0,
        "message": "success",
        "data": TaskResultService.build_result_info(result),
    }


@router.get("/api/tasks/{task_id}/result")
def get_result_by_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    根据任务ID查询联合统计结果
    """
    task_service.get_task_or_404(
        db=db,
        task_id=task_id,
    )

    result = TaskResultService.get_result_by_task_id(
        db=db,
        task_id=task_id,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="该任务暂无统计结果",
        )

    return {
        "code": 0,
        "message": "success",
        "data": TaskResultService.build_result_info(result),
    }