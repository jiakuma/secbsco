"""第5阶段：机构管理 API。"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.schemas.agency_schema import AgencyCreate, AgencyUpdate
from app.services import agency_service
from app.utils.response import success, fail


router = APIRouter(prefix="/api/agencies", tags=["机构管理"])


@router.get("")
def list_agencies(
    keyword: str | None = Query(default=None, description="机构编码/名称"),
    agency_level: str | None = Query(default=None, description="机构层级"),
    agency_type: str | None = Query(default=None, description="机构类型"),
    status: str | None = Query(default=None, description="机构状态"),
    parent_agency_id: int | None = Query(default=None, description="上级机构ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    data = agency_service.list_agencies(
        db=db,
        current_user=current_user,
        keyword=keyword,
        agency_level=agency_level,
        agency_type=agency_type,
        status=status,
        parent_agency_id=parent_agency_id,
        page=page,
        page_size=page_size,
    )
    return success(data)


@router.get("/tree")
def get_agency_tree(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    return success(agency_service.get_agency_tree(db, current_user))


@router.get("/{agency_id}")
def get_agency_detail(
    agency_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    return success(agency_service.get_agency_detail(db, agency_id, current_user))


@router.post("")
def create_agency(
    payload: AgencyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    data = agency_service.create_agency(
        db=db,
        payload=payload.model_dump(exclude_unset=True),
        current_user=current_user,
        request=request,
    )
    return success(data)


@router.put("/{agency_id}")
def update_agency(
    agency_id: int,
    payload: AgencyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    data = agency_service.update_agency(
        db=db,
        agency_id=agency_id,
        payload=payload.model_dump(exclude_unset=True),
        current_user=current_user,
        request=request,
    )
    return success(data)


@router.post("/{agency_id}/enable")
def enable_agency(
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    return success(agency_service.set_agency_status(db, agency_id, "active", current_user, request))


@router.post("/{agency_id}/disable")
def disable_agency(
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    return success(agency_service.set_agency_status(db, agency_id, "disabled", current_user, request))


@router.post("/{agency_id}/delete")
def delete_agency_by_post(
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """物理删除机构：兼容前端用 POST 触发删除，避免 DELETE 路由未更新时出现 405。"""
    return success(agency_service.delete_agency(db, agency_id, current_user, request))


@router.delete("/{agency_id}")
def delete_agency(
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """物理删除机构及其下级机构，同时清理关联的用户、节点、群组关系和存证等数据。"""
    return success(agency_service.delete_agency(db, agency_id, current_user, request))

