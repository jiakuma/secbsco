"""第5阶段：节点管理 API。"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.schemas.node_schema import NodeCreate, NodeUpdate, NodeStatusUpdate
from app.services.node_service import NodeService
from app.utils.response import success


router = APIRouter(prefix="/api/nodes", tags=["节点管理"])


@router.get("")
def list_nodes(
    keyword: Optional[str] = Query(default=None, description="节点编码或节点名称"),
    agency_id: Optional[int] = Query(default=None, description="所属机构ID"),
    status: Optional[str] = Query(default=None, description="节点状态"),
    node_type: Optional[str] = Query(default=None, description="节点类型"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    total, items = NodeService.list_nodes(
        db=db,
        current_user=current_user,
        keyword=keyword,
        agency_id=agency_id,
        status=status,
        node_type=node_type,
        page=page,
        page_size=page_size,
    )
    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [NodeService.build_node_info(item, db) for item in items],
    })


@router.post("")
def create_node(
    node_req: NodeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    node = NodeService.create_node(
        db=db,
        payload=node_req.model_dump(exclude_unset=True),
        current_user=current_user,
        request=request,
    )
    return success(NodeService.build_node_info(node, db))


@router.get("/{node_id}")
def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    node = NodeService.get_node_by_id(db=db, node_id=node_id)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")
    from app.services.resource_permission_service import check_can_manage_node
    check_can_manage_node(db, current_user, node)
    return success(NodeService.build_node_info(node, db))


@router.put("/{node_id}")
def update_node(
    node_id: int,
    node_req: NodeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    node = NodeService.get_node_by_id(db=db, node_id=node_id)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")

    node = NodeService.update_node(
        db=db,
        node=node,
        payload=node_req.model_dump(exclude_unset=True),
        current_user=current_user,
        request=request,
    )
    return success(NodeService.build_node_info(node, db))


@router.put("/{node_id}/status")
def update_node_status(
    node_id: int,
    status_req: NodeStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    node = NodeService.get_node_by_id(db=db, node_id=node_id)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")

    node = NodeService.update_node_status(
        db=db,
        node=node,
        status=status_req.status,
        current_user=current_user,
        request=request,
    )
    return success(NodeService.build_node_info(node, db))


@router.post("/{node_id}/enable")
def enable_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    node = NodeService.get_node_by_id(db=db, node_id=node_id)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")
    node = NodeService.update_node_status(db, node, "active", current_user, request)
    return success(NodeService.build_node_info(node, db))


@router.post("/{node_id}/disable")
def disable_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    node = NodeService.get_node_by_id(db=db, node_id=node_id)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")
    node = NodeService.update_node_status(db, node, "disabled", current_user, request)
    return success(NodeService.build_node_info(node, db))


@router.delete("/{node_id}")
def delete_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """物理删除节点，并清理节点相关授权、日志和存证数据。"""
    node = NodeService.get_node_by_id(db=db, node_id=node_id)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")
    return success(NodeService.delete_node(db=db, node=node, current_user=current_user, request=request))


@router.post("/{node_id}/check")
def check_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """检测节点Agent状态。"""
    node = NodeService.get_node_by_id(db=db, node_id=node_id)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")
    return success(NodeService.check_node(db=db, node=node, current_user=current_user, request=request))


@router.post("/{node_id}/activate")
def activate_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """激活节点。"""
    node = NodeService.get_node_by_id(db=db, node_id=node_id)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")
    return success(NodeService.activate_node(db=db, node=node, current_user=current_user, request=request))


@router.post("/{node_id}/deactivate")
def deactivate_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """停用节点。"""
    node = NodeService.get_node_by_id(db=db, node_id=node_id)
    if not node:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")
    return success(NodeService.deactivate_node(db=db, node=node, current_user=current_user, request=request))
