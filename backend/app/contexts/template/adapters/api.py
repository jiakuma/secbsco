from dataclasses import asdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success
from .persistence import (
    SQLAlchemyTemplateRepository, BridgeAccessControlPort, BridgeAgencyQueryPort,
)
from .schemas import StatTemplateCreate, StatTemplateUpdate
from ..application.use_cases import (
    ListTemplatesUseCase, GetTemplateDetailUseCase, CreateTemplateUseCase, UpdateTemplateUseCase, DeleteTemplateUseCase,
)


router = APIRouter(prefix="/api/stat-templates", tags=["任务模板管理"])


def _get_use_cases(db: Session):
    repo = SQLAlchemyTemplateRepository(db)
    access_control = BridgeAccessControlPort(db)
    agency = BridgeAgencyQueryPort(db)
    return {
        "list": ListTemplatesUseCase(repo, access_control, agency),
        "detail": GetTemplateDetailUseCase(repo, access_control, agency),
        "create": CreateTemplateUseCase(repo, access_control, agency),
        "update": UpdateTemplateUseCase(repo, access_control, agency),
        "delete": DeleteTemplateUseCase(repo, access_control),
    }


def _dto_to_dict(dto) -> dict:
    return asdict(dto)


@router.get("")
def list_stat_templates(
    keyword: str | None = Query(default=None),
    agency_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["list"].execute(current_user, keyword=keyword, agency_id=agency_id, page=page, page_size=page_size)
    return success(_dto_to_dict(result))


@router.post("")
def create_stat_template(
    payload: StatTemplateCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["create"].execute(payload.model_dump(exclude_unset=True), current_user)
    db.commit()
    return success(_dto_to_dict(result))


@router.get("/{template_id}")
def get_stat_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["detail"].execute(template_id, current_user)
    return success(_dto_to_dict(result))


@router.put("/{template_id}")
def update_stat_template(
    template_id: int,
    payload: StatTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["update"].execute(template_id, payload.model_dump(exclude_unset=True), current_user)
    db.commit()
    return success(_dto_to_dict(result))


@router.delete("/{template_id}")
def delete_stat_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["delete"].execute(template_id, current_user, db=db)
    db.commit()
    return success(result)
