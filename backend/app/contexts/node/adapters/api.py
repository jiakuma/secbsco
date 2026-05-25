from dataclasses import asdict
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success
from .persistence import (
    SQLAlchemyNodeRepository, BridgeAccessControlPort, BridgeAuditLogPort,
    BridgeAgencyQueryPort, BridgeAgentPort,
)
from .schemas import NodeCreate, NodeUpdate, NodeStatusUpdate
from ..application.use_cases import (
    ListNodeUseCase, GetNodeDetailUseCase, CreateNodeUseCase, UpdateNodeUseCase,
    UpdateNodeStatusUseCase, DeleteNodeUseCase, CheckNodeUseCase, ActivateNodeUseCase,
    DeactivateNodeUseCase,
)


router = APIRouter(prefix="/api/nodes", tags=["节点管理"])


def _get_use_cases(db: Session):
    repo = SQLAlchemyNodeRepository(db)
    access_control = BridgeAccessControlPort(db)
    audit = BridgeAuditLogPort()
    agency = BridgeAgencyQueryPort(db)
    agent = BridgeAgentPort()
    return {
        "list": ListNodeUseCase(repo, access_control, agency),
        "detail": GetNodeDetailUseCase(repo, access_control, agency),
        "create": CreateNodeUseCase(repo, access_control, audit, agency),
        "update": UpdateNodeUseCase(repo, access_control, audit, agency),
        "status": UpdateNodeStatusUseCase(repo, access_control, audit, agency),
        "delete": DeleteNodeUseCase(repo, access_control, audit),
        "check": CheckNodeUseCase(repo, access_control, audit, agency, agent),
        "activate": ActivateNodeUseCase(repo, access_control, audit, agency, agent),
        "deactivate": DeactivateNodeUseCase(repo, access_control, audit, agency, agent),
    }


def _dto_to_dict(dto) -> dict:
    return asdict(dto)


@router.get("")
def list_nodes(
    keyword: str | None = Query(default=None),
    agency_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    node_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["list"].execute(current_user, keyword=keyword, agency_id=agency_id,
                                 status=status, node_type=node_type, page=page, page_size=page_size)
    return success(_dto_to_dict(result))


@router.post("")
def create_node(
    payload: NodeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["create"].execute(payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.get("/{node_id}")
def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["detail"].execute(node_id, current_user)
    return success(_dto_to_dict(result))


@router.put("/{node_id}")
def update_node(
    node_id: int,
    payload: NodeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["update"].execute(node_id, payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.put("/{node_id}/status")
def update_node_status(
    node_id: int,
    status_req: NodeStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["status"].execute(node_id, status_req.status, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{node_id}/enable")
def enable_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["status"].execute(node_id, "active", current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{node_id}/disable")
def disable_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["status"].execute(node_id, "disabled", current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.delete("/{node_id}")
def delete_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["delete"].execute(node_id, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{node_id}/check")
def check_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["check"].execute(node_id, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{node_id}/activate")
def activate_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["activate"].execute(node_id, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{node_id}/deactivate")
def deactivate_node(
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["deactivate"].execute(node_id, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))
