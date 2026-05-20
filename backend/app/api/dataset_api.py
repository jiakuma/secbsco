from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.models.dataset import Dataset
from app.models.agency import Agency
from app.models.node import Node
from app.schemas.dataset_schema import (
    DatasetCreate,
    DatasetUpdate,
)
from app.services.dataset_service import DatasetService
from app.services.access_control_service import (
    is_platform_admin,
    is_agency_admin,
    is_ancestor_agency,
)


router = APIRouter(
    prefix="/api/datasets",
    tags=["数据集管理"]
)


def _get_visible_agency_ids(db: Session, user: SysUser) -> list[int] | None:
    """获取用户可见机构ID列表，None表示全部可见"""
    if is_platform_admin(db, user.id):
        return None
    
    user_agency_id = user.agency_id
    if not user_agency_id:
        return []
    
    agency_ids = [user_agency_id]
    if is_agency_admin(db, user.id):
        def collect_descendants(parent_id: int):
            children = db.query(Agency.id).filter(
                Agency.parent_agency_id == parent_id,
                Agency.status == "active",
            ).all()
            for child in children:
                child_id = child[0]
                if child_id not in agency_ids:
                    agency_ids.append(child_id)
                    collect_descendants(child_id)
        collect_descendants(user_agency_id)
    
    return agency_ids


def _check_dataset_access(db: Session, user: SysUser, dataset: Dataset, require_write: bool = False):
    """检查数据集访问权限"""
    if is_platform_admin(db, user.id):
        return
    
    if require_write and not is_agency_admin(db, user.id):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    user_agency_id = user.agency_id
    dataset_agency_id = dataset.agency_id
    
    if user_agency_id == dataset_agency_id:
        return
    
    if is_agency_admin(db, user.id) and is_ancestor_agency(db, user_agency_id, dataset_agency_id):
        return
    
    raise HTTPException(status_code=403, detail="无权访问该数据集")


@router.get("")
def list_datasets(
    keyword: Optional[str] = Query(default=None, description="关键词搜索名称或编码"),
    agency_id: Optional[int] = Query(default=None, description="所属机构ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询数据集列表"""
    visible_agency_ids = _get_visible_agency_ids(db, current_user)
    
    query = db.query(Dataset)
    
    if visible_agency_ids is not None:
        query = query.filter(Dataset.agency_id.in_(visible_agency_ids))
    
    if keyword:
        query = query.filter(
            (Dataset.dataset_code.like(f"%{keyword}%")) |
            (Dataset.dataset_name.like(f"%{keyword}%"))
        )
    
    if agency_id:
        if visible_agency_ids is not None and agency_id not in visible_agency_ids:
            return {"code": 0, "message": "success", "data": {"total": 0, "page": page, "page_size": page_size, "items": []}}
        query = query.filter(Dataset.agency_id == agency_id)
    
    total = query.count()
    items = query.order_by(Dataset.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [_build_dataset_info(item, db) for item in items]
        }
    }


def _build_dataset_info(dataset: Dataset, db: Session) -> dict:
    agency = db.query(Agency).filter(Agency.id == dataset.agency_id).first()
    node = db.query(Node).filter(Node.id == dataset.node_id).first() if dataset.node_id else None
    
    return {
        "id": dataset.id,
        "dataset_code": dataset.dataset_code,
        "dataset_name": dataset.dataset_name,
        "agency_id": dataset.agency_id,
        "agency_name": agency.agency_name if agency else None,
        "node_id": dataset.node_id,
        "node_name": node.node_name if node else None,
        "data_type": dataset.data_type,
        "data_location": dataset.data_location,
        "description": dataset.description,
        "created_at": str(dataset.created_at) if dataset.created_at else None,
        "updated_at": str(dataset.updated_at) if dataset.updated_at else None,
    }


@router.post("")
def create_dataset(
    dataset_req: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """新增数据集"""
    if not is_platform_admin(db, current_user.id) and not is_agency_admin(db, current_user.id):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    visible_agency_ids = _get_visible_agency_ids(db, current_user)
    if visible_agency_ids is not None and dataset_req.agency_id not in visible_agency_ids:
        raise HTTPException(status_code=403, detail="无权在该机构下创建数据集")
    
    existed = db.query(Dataset).filter(Dataset.dataset_code == dataset_req.dataset_code).first()
    if existed:
        raise HTTPException(status_code=400, detail="数据集编码已存在")
    
    dataset = Dataset(
        agency_id=dataset_req.agency_id,
        node_id=getattr(dataset_req, 'node_id', None),
        dataset_code=dataset_req.dataset_code,
        dataset_name=dataset_req.dataset_name,
        data_type=getattr(dataset_req, 'data_type', None),
        data_location=getattr(dataset_req, 'data_location', None),
        description=getattr(dataset_req, 'description', None),
        created_by=current_user.id,
    )
    
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    return {"code": 0, "message": "success", "data": _build_dataset_info(dataset, db)}


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询数据集详情"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    _check_dataset_access(db, current_user, dataset)
    
    return {"code": 0, "message": "success", "data": _build_dataset_info(dataset, db)}


@router.put("/{dataset_id}")
def update_dataset(
    dataset_id: int,
    dataset_req: DatasetUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """修改数据集"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    _check_dataset_access(db, current_user, dataset, require_write=True)
    
    update_data = dataset_req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dataset, key, value)
    
    db.commit()
    db.refresh(dataset)
    
    return {"code": 0, "message": "success", "data": _build_dataset_info(dataset, db)}


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """删除数据集"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    _check_dataset_access(db, current_user, dataset, require_write=True)
    
    db.delete(dataset)
    db.commit()
    
    return {"code": 0, "message": "success", "data": {"id": dataset_id}}