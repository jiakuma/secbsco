from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.schemas.stat_template_schema import (
    StatTemplateCreate,
    StatTemplateUpdate,
    StatTemplateStatusUpdate,
)
from app.services.stat_template_service import StatTemplateService


router = APIRouter(
    prefix="/api/stat-templates",
    tags=["统计模板管理"]
)


@router.get("")
def list_stat_templates(
    keyword: Optional[str] = Query(default=None, description="模板编码或模板名称"),
    stat_type: Optional[str] = Query(default=None, description="统计类型"),
    status: Optional[str] = Query(default=None, description="模板状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    查询统计模板列表
    """
    total, items = StatTemplateService.list_templates(
        db=db,
        keyword=keyword,
        stat_type=stat_type,
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
                StatTemplateService.build_template_info(item)
                for item in items
            ]
        }
    }


@router.post("")
def create_stat_template(
    template_req: StatTemplateCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    新增统计模板
    """
    existed = StatTemplateService.get_template_by_code(
        db=db,
        template_code=template_req.template_code
    )

    if existed:
        raise HTTPException(
            status_code=400,
            detail="模板编码已存在"
        )

    if template_req.status not in ["enabled", "disabled"]:
        raise HTTPException(
            status_code=400,
            detail="模板状态只能是 enabled 或 disabled"
        )

    template = StatTemplateService.create_template(
        db=db,
        template_req=template_req
    )

    return {
        "code": 0,
        "message": "success",
        "data": StatTemplateService.build_template_info(template)
    }


@router.get("/{template_id}")
def get_stat_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    查询统计模板详情
    """
    template = StatTemplateService.get_template_by_id(
        db=db,
        template_id=template_id
    )

    if not template:
        raise HTTPException(
            status_code=404,
            detail="统计模板不存在"
        )

    return {
        "code": 0,
        "message": "success",
        "data": StatTemplateService.build_template_info(template)
    }


@router.put("/{template_id}")
def update_stat_template(
    template_id: int,
    template_req: StatTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    修改统计模板
    """
    template = StatTemplateService.get_template_by_id(
        db=db,
        template_id=template_id
    )

    if not template:
        raise HTTPException(
            status_code=404,
            detail="统计模板不存在"
        )

    template = StatTemplateService.update_template(
        db=db,
        template=template,
        template_req=template_req
    )

    return {
        "code": 0,
        "message": "success",
        "data": StatTemplateService.build_template_info(template)
    }


@router.put("/{template_id}/status")
def update_stat_template_status(
    template_id: int,
    status_req: StatTemplateStatusUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    启用 / 禁用统计模板
    """
    if status_req.status not in ["enabled", "disabled"]:
        raise HTTPException(
            status_code=400,
            detail="模板状态只能是 enabled 或 disabled"
        )

    template = StatTemplateService.get_template_by_id(
        db=db,
        template_id=template_id
    )

    if not template:
        raise HTTPException(
            status_code=404,
            detail="统计模板不存在"
        )

    template = StatTemplateService.update_template_status(
        db=db,
        template=template,
        status=status_req.status
    )

    return {
        "code": 0,
        "message": "success",
        "data": StatTemplateService.build_template_info(template)
    }