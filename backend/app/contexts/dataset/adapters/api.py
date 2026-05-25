from dataclasses import asdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success
from .persistence import (
    SQLAlchemyDatasetRepository, BridgeAccessControlPort, BridgeAgencyQueryPort, BridgeNodeQueryPort,
)
from .schemas import DatasetCreate, DatasetUpdate
from ..application.use_cases import (
    ListDatasetsUseCase, GetDatasetDetailUseCase, CreateDatasetUseCase, UpdateDatasetUseCase, DeleteDatasetUseCase,
)


router = APIRouter(prefix="/api/datasets", tags=["数据集管理"])


def _get_use_cases(db: Session):
    repo = SQLAlchemyDatasetRepository(db)
    access_control = BridgeAccessControlPort(db)
    agency = BridgeAgencyQueryPort(db)
    node = BridgeNodeQueryPort(db)
    return {
        "list": ListDatasetsUseCase(repo, access_control, agency, node),
        "detail": GetDatasetDetailUseCase(repo, access_control, agency, node),
        "create": CreateDatasetUseCase(repo, access_control, agency, node),
        "update": UpdateDatasetUseCase(repo, access_control, agency, node),
        "delete": DeleteDatasetUseCase(repo, access_control),
    }


def _dto_to_dict(dto) -> dict:
    return asdict(dto)


@router.get("")
def list_datasets(
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
def create_dataset(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["create"].execute(payload.model_dump(exclude_unset=True), current_user)
    db.commit()
    return success(_dto_to_dict(result))


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["detail"].execute(dataset_id, current_user)
    return success(_dto_to_dict(result))


@router.put("/{dataset_id}")
def update_dataset(
    dataset_id: int,
    payload: DatasetUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["update"].execute(dataset_id, payload.model_dump(exclude_unset=True), current_user)
    db.commit()
    return success(_dto_to_dict(result))


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["delete"].execute(dataset_id, current_user)
    db.commit()
    return success(result)
