from dataclasses import asdict
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success, fail
from ..adapters.persistence import (
    SQLAlchemyUserRepository, BridgeAuthPort, BridgeAccessControlPort, BridgeAuditLogPort,
    BridgeRoleBindingPort, BridgeUserGroupPort, BridgeAgencyQueryPort,
)
from ..adapters.schemas import UserCreate, UserUpdate, RoleBindRequest, GroupBindRequest
from ..application.use_cases import (
    ListUsersUseCase, GetUserDetailUseCase, CreateUserUseCase, UpdateUserUseCase,
    EnableUserUseCase, DisableUserUseCase, DeleteUserUseCase,
)


router = APIRouter(prefix="/api/users", tags=["用户管理"])


def _get_use_cases(db: Session):
    repo = SQLAlchemyUserRepository(db)
    access_control = BridgeAccessControlPort(db)
    audit = BridgeAuditLogPort()
    agency = BridgeAgencyQueryPort(db)
    return {
        "list": ListUsersUseCase(repo, access_control, agency),
        "detail": GetUserDetailUseCase(repo, agency),
        "create": CreateUserUseCase(repo, BridgeAuthPort(db), audit, agency),
        "update": UpdateUserUseCase(repo, audit, agency),
        "enable": EnableUserUseCase(repo, audit, agency),
        "disable": DisableUserUseCase(repo, audit, agency),
        "delete": DeleteUserUseCase(repo, audit),
        "roles": BridgeRoleBindingPort(db),
        "groups": BridgeUserGroupPort(db),
    }


def _dto_to_dict(dto) -> dict:
    return asdict(dto)


@router.get("")
def list_users(
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    agency_id: int | None = Query(default=None),
    role_code: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["list"].execute(current_user, keyword=keyword, status=status,
                                 agency_id=agency_id, role_code=role_code,
                                 page=page, page_size=page_size)
    return success(_dto_to_dict(result))


@router.get("/switch-options")
def get_switch_user_options(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    users = db.query(SysUser).filter(SysUser.status == "active").all()
    return success([{"id": u.id, "username": u.username, "real_name": u.real_name} for u in users])


@router.get("/{user_id}")
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["detail"].execute(user_id)
    return success(_dto_to_dict(result))


@router.post("")
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["create"].execute(payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["update"].execute(user_id, payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{user_id}/enable")
def enable_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["enable"].execute(user_id, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{user_id}/disable")
def disable_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["disable"].execute(user_id, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["delete"].execute(user_id, current_user, db=db, request=request)
    db.commit()
    return success(result)


@router.get("/{user_id}/roles")
def get_user_roles(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    roles = ucs["roles"].get_user_roles(user_id)
    return success(roles)


@router.post("/{user_id}/roles")
def bind_user_role(
    user_id: int,
    payload: RoleBindRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["roles"].bind_role(user_id, payload.role_code, payload.scope_type, payload.scope_id, current_user, request)
    db.commit()
    return success(result)


@router.delete("/{user_id}/roles/{binding_id}")
def unbind_user_role(
    user_id: int,
    binding_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    ucs["roles"].unbind_role(binding_id)
    db.commit()
    return success(message="解绑成功")


@router.get("/{user_id}/groups")
def get_user_groups(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    groups = ucs["groups"].get_user_groups(user_id)
    return success(groups)


@router.post("/{user_id}/groups")
def add_user_to_group(
    user_id: int,
    payload: GroupBindRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    result = ucs["groups"].add_user_to_group(user_id, payload.group_id, payload.agency_id, current_user, request)
    db.commit()
    return success(result)


@router.delete("/{user_id}/groups/{group_id}")
def remove_user_from_group(
    user_id: int,
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    ucs = _get_use_cases(db)
    ucs["groups"].remove_user_from_group(user_id, group_id)
    db.commit()
    return success(message="移出成功")
