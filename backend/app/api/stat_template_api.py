from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.models.stat_template import StatTemplate
from app.models.agency import Agency
from app.schemas.stat_template_schema import (
    StatTemplateCreate,
    StatTemplateUpdate,
)
from app.services.access_control_service import (
    is_platform_admin,
    is_agency_admin,
    is_ancestor_agency,
)


router = APIRouter(
    prefix="/api/stat-templates",
    tags=["任务模板管理"]
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


def _check_template_access(db: Session, user: SysUser, template: StatTemplate, require_write: bool = False):
    """检查模板访问权限"""
    if is_platform_admin(db, user.id):
        return
    
    if require_write and not is_agency_admin(db, user.id):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    if not template.agency_id:
        return
    
    user_agency_id = user.agency_id
    template_agency_id = template.agency_id
    
    if user_agency_id == template_agency_id:
        return
    
    if is_agency_admin(db, user.id) and is_ancestor_agency(db, user_agency_id, template_agency_id):
        return
    
    raise HTTPException(status_code=403, detail="无权访问该模板")


@router.get("")
def list_stat_templates(
    keyword: Optional[str] = Query(default=None, description="关键词搜索名称或编码"),
    agency_id: Optional[int] = Query(default=None, description="所属机构ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询任务模板列表"""
    visible_agency_ids = _get_visible_agency_ids(db, current_user)
    
    query = db.query(StatTemplate)
    
    if keyword:
        query = query.filter(
            (StatTemplate.template_code.like(f"%{keyword}%")) |
            (StatTemplate.template_name.like(f"%{keyword}%"))
        )
    
    if agency_id:
        if visible_agency_ids is not None and agency_id not in visible_agency_ids:
            return {"code": 0, "message": "success", "data": {"total": 0, "page": page, "page_size": page_size, "items": []}}
        query = query.filter(StatTemplate.agency_id == agency_id)
    
    if visible_agency_ids is not None:
        query = query.filter(
            (StatTemplate.agency_id.in_(visible_agency_ids)) | (StatTemplate.agency_id.is_(None))
        )
    
    total = query.count()
    items = query.order_by(StatTemplate.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [_build_template_info(item, db) for item in items]
        }
    }


def _build_template_info(template: StatTemplate, db: Session) -> dict:
    agency = db.query(Agency).filter(Agency.id == template.agency_id).first() if template.agency_id else None
    
    return {
        "id": template.id,
        "template_code": template.template_code,
        "template_name": template.template_name,
        "agency_id": template.agency_id,
        "agency_name": agency.agency_name if agency else None,
        "scenario": template.scenario,
        "exec_mode": template.exec_mode,
        "output_type": template.output_type,
        "description": template.description,
        "created_at": str(template.created_at) if template.created_at else None,
        "updated_at": str(template.updated_at) if template.updated_at else None,
    }


@router.post("")
def create_stat_template(
    template_req: StatTemplateCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """新增任务模板"""
    if not is_platform_admin(db, current_user.id) and not is_agency_admin(db, current_user.id):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    agency_id = getattr(template_req, 'agency_id', None) or current_user.agency_id
    visible_agency_ids = _get_visible_agency_ids(db, current_user)
    
    if agency_id and visible_agency_ids is not None and agency_id not in visible_agency_ids:
        raise HTTPException(status_code=403, detail="无权在该机构下创建模板")
    
    existed = db.query(StatTemplate).filter(StatTemplate.template_code == template_req.template_code).first()
    if existed:
        raise HTTPException(status_code=400, detail="模板编码已存在")
    
    template = StatTemplate(
        agency_id=agency_id,
        template_code=template_req.template_code,
        template_name=template_req.template_name,
        scenario=getattr(template_req, 'scenario', None),
        exec_mode=getattr(template_req, 'exec_mode', None),
        output_type=getattr(template_req, 'output_type', None),
        description=getattr(template_req, 'description', None),
        created_by=current_user.id,
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return {"code": 0, "message": "success", "data": _build_template_info(template, db)}


@router.get("/{template_id}")
def get_stat_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询任务模板详情"""
    template = db.query(StatTemplate).filter(StatTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    _check_template_access(db, current_user, template)
    
    return {"code": 0, "message": "success", "data": _build_template_info(template, db)}


@router.put("/{template_id}")
def update_stat_template(
    template_id: int,
    template_req: StatTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """修改任务模板"""
    template = db.query(StatTemplate).filter(StatTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    _check_template_access(db, current_user, template, require_write=True)
    
    update_data = template_req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)
    
    db.commit()
    db.refresh(template)
    
    return {"code": 0, "message": "success", "data": _build_template_info(template, db)}


@router.delete("/{template_id}")
def delete_stat_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """删除任务模板（物理删除，清理相关引用）"""
    template = db.query(StatTemplate).filter(StatTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    _check_template_access(db, current_user, template, require_write=True)
    
    protected_codes = [
        "T1_JOINT_CASE_STAT_TEMPLATE",
        "T2_SPATIOTEMPORAL_TEMPLATE",
        "T3_KEY_POPULATION_RISK_TEMPLATE",
    ]
    if template.template_code in protected_codes:
        raise HTTPException(status_code=403, detail="该模板为系统核心模板，不允许删除")
    
    from app.models.group import GroupTaskTemplate
    from app.models.task import Task
    
    db.query(GroupTaskTemplate).filter(GroupTaskTemplate.template_id == template_id).delete()
    
    db.query(Task).filter(Task.template_id == template_id).update({Task.template_id: None})
    
    db.delete(template)
    db.commit()
    
    return {"code": 0, "message": "success", "data": {"id": template_id}}