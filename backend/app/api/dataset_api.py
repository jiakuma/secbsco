from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.schemas.dataset_schema import (
    DatasetCreate,
    DatasetUpdate,
    DatasetStatusUpdate,
)
from app.services.dataset_service import DatasetService


router = APIRouter(
    prefix="/api/datasets",
    tags=["数据集管理"]
)


@router.get("")
def list_datasets(
    keyword: Optional[str] = Query(default=None, description="数据集编码或数据集名称"),
    agency_id: Optional[int] = Query(default=None, description="所属机构ID"),
    dataset_type: Optional[str] = Query(default=None, description="数据集类型"),
    status: Optional[str] = Query(default=None, description="数据集状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    查询数据集列表
    """
    total, items = DatasetService.list_datasets(
        db=db,
        keyword=keyword,
        agency_id=agency_id,
        dataset_type=dataset_type,
        status=status,
        page=page,
        page_size=page_size
    )

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                DatasetService.build_dataset_info(item)
                for item in items
            ]
        }
    }


@router.post("")
def create_dataset(
    dataset_req: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    新增数据集
    """
    agency = DatasetService.get_agency_by_id(
        db=db,
        agency_id=dataset_req.agency_id
    )

    if not agency:
        raise HTTPException(
            status_code=404,
            detail="所属机构不存在"
        )

    existed = DatasetService.get_dataset_by_code(
        db=db,
        dataset_code=dataset_req.dataset_code
    )

    if existed:
        raise HTTPException(
            status_code=400,
            detail="数据集编码已存在"
        )

    if dataset_req.status not in ["enabled", "disabled"]:
        raise HTTPException(
            status_code=400,
            detail="数据集状态只能是 enabled 或 disabled"
        )

    dataset = DatasetService.create_dataset(
        db=db,
        dataset_req=dataset_req
    )

    return {
        "code": 0,
        "message": "success",
        "data": DatasetService.build_dataset_info(dataset)
    }


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    查询数据集详情
    """
    dataset = DatasetService.get_dataset_by_id(
        db=db,
        dataset_id=dataset_id
    )

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail="数据集不存在"
        )

    return {
        "code": 0,
        "message": "success",
        "data": DatasetService.build_dataset_info(dataset)
    }


@router.put("/{dataset_id}")
def update_dataset(
    dataset_id: int,
    dataset_req: DatasetUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    修改数据集信息
    """
    dataset = DatasetService.get_dataset_by_id(
        db=db,
        dataset_id=dataset_id
    )

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail="数据集不存在"
        )

    if dataset_req.agency_id is not None:
        agency = DatasetService.get_agency_by_id(
            db=db,
            agency_id=dataset_req.agency_id
        )

        if not agency:
            raise HTTPException(
                status_code=404,
                detail="所属机构不存在"
            )

    dataset = DatasetService.update_dataset(
        db=db,
        dataset=dataset,
        dataset_req=dataset_req
    )

    return {
        "code": 0,
        "message": "success",
        "data": DatasetService.build_dataset_info(dataset)
    }


@router.put("/{dataset_id}/status")
def update_dataset_status(
    dataset_id: int,
    status_req: DatasetStatusUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    启用 / 禁用数据集
    """
    if status_req.status not in ["enabled", "disabled"]:
        raise HTTPException(
            status_code=400,
            detail="数据集状态只能是 enabled 或 disabled"
        )

    dataset = DatasetService.get_dataset_by_id(
        db=db,
        dataset_id=dataset_id
    )

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail="数据集不存在"
        )

    dataset = DatasetService.update_dataset_status(
        db=db,
        dataset=dataset,
        status=status_req.status
    )

    return {
        "code": 0,
        "message": "success",
        "data": DatasetService.build_dataset_info(dataset)
    }