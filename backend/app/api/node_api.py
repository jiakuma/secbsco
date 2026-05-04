from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.schemas.node_schema import (
    NodeCreate,
    NodeUpdate,
    NodeStatusUpdate,
)
from app.services.node_service import NodeService


router = APIRouter(
    prefix="/api/nodes",
    tags=["节点管理"]
)


@router.get("")
def list_nodes(
    keyword: Optional[str] = Query(default=None, description="节点编码或节点名称"),
    agency_id: Optional[int] = Query(default=None, description="所属机构ID"),
    status: Optional[str] = Query(default=None, description="节点状态"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    查询节点列表
    """
    total, items = NodeService.list_nodes(
        db=db,
        keyword=keyword,
        agency_id=agency_id,
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
                NodeService.build_node_info(item)
                for item in items
            ]
        }
    }


@router.post("")
def create_node(
    node_req: NodeCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    新增节点
    """
    agency = NodeService.get_agency_by_id(
        db=db,
        agency_id=node_req.agency_id
    )

    if not agency:
        raise HTTPException(
            status_code=404,
            detail="所属机构不存在"
        )

    existed = NodeService.get_node_by_code(
        db=db,
        node_code=node_req.node_code
    )

    if existed:
        raise HTTPException(
            status_code=400,
            detail="节点编码已存在"
        )

    if node_req.status not in ["online", "offline", "disabled"]:
        raise HTTPException(
            status_code=400,
            detail="节点状态只能是 online、offline 或 disabled"
        )

    node = NodeService.create_node(
        db=db,
        node_req=node_req
    )

    return {
        "code": 0,
        "message": "success",
        "data": NodeService.build_node_info(node)
    }


@router.get("/{node_id}")
def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    查询节点详情
    """
    node = NodeService.get_node_by_id(
        db=db,
        node_id=node_id
    )

    if not node:
        raise HTTPException(
            status_code=404,
            detail="节点不存在"
        )

    return {
        "code": 0,
        "message": "success",
        "data": NodeService.build_node_info(node)
    }


@router.put("/{node_id}")
def update_node(
    node_id: int,
    node_req: NodeUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    编辑节点信息
    """
    node = NodeService.get_node_by_id(
        db=db,
        node_id=node_id
    )

    if not node:
        raise HTTPException(
            status_code=404,
            detail="节点不存在"
        )

    if node_req.agency_id is not None:
        agency = NodeService.get_agency_by_id(
            db=db,
            agency_id=node_req.agency_id
        )

        if not agency:
            raise HTTPException(
                status_code=404,
                detail="所属机构不存在"
            )

    node = NodeService.update_node(
        db=db,
        node=node,
        node_req=node_req
    )

    return {
        "code": 0,
        "message": "success",
        "data": NodeService.build_node_info(node)
    }


@router.put("/{node_id}/status")
def update_node_status(
    node_id: int,
    status_req: NodeStatusUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    更新节点状态
    """
    if status_req.status not in ["online", "offline", "disabled"]:
        raise HTTPException(
            status_code=400,
            detail="节点状态只能是 online、offline 或 disabled"
        )

    node = NodeService.get_node_by_id(
        db=db,
        node_id=node_id
    )

    if not node:
        raise HTTPException(
            status_code=404,
            detail="节点不存在"
        )

    node = NodeService.update_node_status(
        db=db,
        node=node,
        status=status_req.status
    )

    return {
        "code": 0,
        "message": "success",
        "data": NodeService.build_node_info(node)
    }