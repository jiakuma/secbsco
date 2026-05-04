from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.schemas.agency_schema import (
    AgencyCreate,
    AgencyUpdate,
    AgencyStatusUpdate,
)
from app.services.agency_service import AgencyService


router = APIRouter(
    prefix="/api/agencies",
    tags=["机构管理"]
)


@router.get("")
def list_agencies(
    keyword: Optional[str] = Query(default=None, description="机构编码或机构名称"),
    status: Optional[str] = Query(default=None, description="机构状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    查询机构列表
    """
    total, items = AgencyService.list_agencies(
        db=db,
        keyword=keyword,
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
                AgencyService.build_agency_info(item)
                for item in items
            ]
        }
    }


@router.post("")
def create_agency(
    agency_req: AgencyCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    新增机构
    """
    existed = AgencyService.get_agency_by_code(
        db=db,
        agency_code=agency_req.agency_code
    )

    if existed:
        raise HTTPException(
            status_code=400,
            detail="机构编码已存在"
        )

    agency = AgencyService.create_agency(
        db=db,
        agency_req=agency_req
    )

    return {
        "code": 0,
        "message": "success",
        "data": AgencyService.build_agency_info(agency)
    }


@router.get("/{agency_id}")
def get_agency(
    agency_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    查询机构详情
    """
    agency = AgencyService.get_agency_by_id(
        db=db,
        agency_id=agency_id
    )

    if not agency:
        raise HTTPException(
            status_code=404,
            detail="机构不存在"
        )

    return {
        "code": 0,
        "message": "success",
        "data": AgencyService.build_agency_info(agency)
    }


@router.put("/{agency_id}")
def update_agency(
    agency_id: int,
    agency_req: AgencyUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    编辑机构信息
    """
    agency = AgencyService.get_agency_by_id(
        db=db,
        agency_id=agency_id
    )

    if not agency:
        raise HTTPException(
            status_code=404,
            detail="机构不存在"
        )

    agency = AgencyService.update_agency(
        db=db,
        agency=agency,
        agency_req=agency_req
    )

    return {
        "code": 0,
        "message": "success",
        "data": AgencyService.build_agency_info(agency)
    }


@router.put("/{agency_id}/status")
def update_agency_status(
    agency_id: int,
    status_req: AgencyStatusUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    启用 / 禁用机构
    """
    if status_req.status not in ["enabled", "disabled"]:
        raise HTTPException(
            status_code=400,
            detail="机构状态只能是 enabled 或 disabled"
        )

    agency = AgencyService.get_agency_by_id(
        db=db,
        agency_id=agency_id
    )

    if not agency:
        raise HTTPException(
            status_code=404,
            detail="机构不存在"
        )

    agency = AgencyService.update_agency_status(
        db=db,
        agency=agency,
        status=status_req.status
    )

    return {
        "code": 0,
        "message": "success",
        "data": AgencyService.build_agency_info(agency)
    }