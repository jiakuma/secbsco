from dataclasses import asdict
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success, fail
from ..adapters.persistence import SQLAlchemyAgencyRepository
from ..adapters.permission_and_audit import AccessControlPermissionAdapter, ResourceChainAuditAdapter
from ..application.use_cases import (
    ListAgenciesUseCase,
    GetAgencyTreeUseCase,
    GetAgencyDetailUseCase,
    CreateAgencyUseCase,
    UpdateAgencyUseCase,
    SetAgencyStatusUseCase,
    DeleteAgencyUseCase,
)
from ..adapters.schemas import AgencyCreate, AgencyUpdate


router = APIRouter(prefix="/api/agencies", tags=["机构管理"])


def _get_use_cases(db: Session):
    repo = SQLAlchemyAgencyRepository(db)
    permission = AccessControlPermissionAdapter(db)
    audit = ResourceChainAuditAdapter(db)
    return {
        "list": ListAgenciesUseCase(repo, permission),
        "tree": GetAgencyTreeUseCase(repo, permission),
        "detail": GetAgencyDetailUseCase(repo, permission),
        "create": CreateAgencyUseCase(repo, permission, audit),
        "update": UpdateAgencyUseCase(repo, permission, audit),
        "set_status": SetAgencyStatusUseCase(repo, permission, audit),
        "delete": DeleteAgencyUseCase(repo, permission, audit),
    }


def _dto_to_dict(dto) -> dict:
    d = asdict(dto)
    for key, val in d.items():
        if hasattr(val, "__dataclass_fields__"):
            d[key] = asdict(val)
    return d


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
    ucs = _get_use_cases(db)
    result = ucs["list"].execute(
        current_user, keyword=keyword, agency_level=agency_level,
        agency_type=agency_type, status=status,
        parent_agency_id=parent_agency_id, page=page, page_size=page_size,
    )
    data = _dto_to_dict(result)
    return success(data)


@router.get("/tree")
def get_agency_tree(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["tree"].execute(current_user)
    return success(result)


@router.get("/{agency_id}")
def get_agency_detail(
    agency_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["detail"].execute(agency_id, current_user)
    return success(_dto_to_dict(result))


@router.post("")
def create_agency(
    payload: AgencyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["create"].execute(payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.put("/{agency_id}")
def update_agency(
    agency_id: int,
    payload: AgencyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["update"].execute(agency_id, payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{agency_id}/enable")
def enable_agency(
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["set_status"].execute(agency_id, "active", current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{agency_id}/disable")
def disable_agency(
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["set_status"].execute(agency_id, "disabled", current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{agency_id}/delete")
def delete_agency_by_post(
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["delete"].execute(agency_id, current_user, request)
    return success(_dto_to_dict(result))


@router.delete("/{agency_id}")
def delete_agency(
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["delete"].execute(agency_id, current_user, request)
    return success(_dto_to_dict(result))
