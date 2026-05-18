"""第5阶段：用户管理 API：用户 CRUD、启用禁用、角色绑定、群组绑定。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import bindparam, inspect, or_, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import get_password_hash
from app.models.agency import Agency
from app.models.group import GroupInfo, GroupMember
from app.models.sys_user import SysUser
from app.models.user import SysUserGroup, SysUserRoleBinding
from app.schemas.user_schema import UserCreate, UserUpdate, RoleBindRequest, GroupBindRequest
from app.services.access_control_service import (
    check_group_admin_access,
    is_platform_admin,
    write_operate_log,
)
from app.services.resource_chain_service import anchor_resource_operation, object_to_dict
from app.services.resource_permission_service import (
    get_manageable_agency_ids,
    require_agency_in_scope,
    check_can_manage_user,
)
from app.utils.response import success, fail


router = APIRouter(prefix="/api/users", tags=["用户管理"])


# ============================================================
# 辅助函数
# ============================================================

def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _normalize_ids(values) -> list[int]:
    result: list[int] = []
    for value in values or []:
        if value is None:
            continue
        if isinstance(value, tuple):
            value = value[0]
        result.append(int(value))
    return sorted(set(result))


def _table_columns(db: Session, table_name: str) -> set[str]:
    inspector = inspect(db.bind)
    if not inspector.has_table(table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _delete_by_values(db: Session, table_name: str, column_name: str, values) -> None:
    ids = _normalize_ids(values)
    if not ids:
        return
    columns = _table_columns(db, table_name)
    if column_name not in columns:
        return
    stmt = text(f"DELETE FROM `{table_name}` WHERE `{column_name}` IN :values").bindparams(
        bindparam("values", expanding=True)
    )
    db.execute(stmt, {"values": ids})


def _delete_chain_records(db: Session, resource_type: str, resource_ids) -> None:
    ids = _normalize_ids(resource_ids)
    columns = _table_columns(db, "chain_record")
    if not ids or not {"resource_type", "resource_id"}.issubset(columns):
        return
    stmt = text(
        "DELETE FROM `chain_record` "
        "WHERE `resource_type` = :resource_type AND `resource_id` IN :resource_ids"
    ).bindparams(bindparam("resource_ids", expanding=True))
    db.execute(stmt, {"resource_type": resource_type, "resource_ids": ids})


def _delete_operate_logs(db: Session, resource_type: str, resource_ids) -> None:
    ids = _normalize_ids(resource_ids)
    columns = _table_columns(db, "sys_user_operate_log")
    if not ids or not {"resource_type", "resource_id"}.issubset(columns):
        return
    stmt = text(
        "DELETE FROM `sys_user_operate_log` "
        "WHERE `resource_type` = :resource_type AND `resource_id` IN :resource_ids"
    ).bindparams(bindparam("resource_ids", expanding=True))
    db.execute(stmt, {"resource_type": resource_type, "resource_ids": ids})


def _agency_name(db: Session, agency_id: int | None) -> str | None:
    if not agency_id:
        return None
    agency = db.query(Agency).filter(Agency.id == agency_id).first()
    return agency.agency_name if agency else None


def _user_to_dict(user: SysUser, db: Session) -> dict:
    roles = (
        db.query(SysUserRoleBinding)
        .filter(SysUserRoleBinding.user_id == user.id, SysUserRoleBinding.status == "active")
        .order_by(SysUserRoleBinding.id.desc())
        .all()
    )
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "phone": user.phone,
        "email": user.email,
        "agency_id": user.agency_id,
        "agency_name": _agency_name(db, user.agency_id),
        "status": user.status,
        "last_login_time": _format_dt(user.last_login_time or user.last_login_at),
        "created_at": _format_dt(user.created_at),
        "updated_at": _format_dt(user.updated_at),
        "roles": [
            {
                "id": r.id,
                "role_code": r.role_code,
                "scope_type": r.scope_type,
                "scope_id": r.scope_id,
                "status": r.status,
            }
            for r in roles
        ],
    }


def _require_user_scope(db: Session, current_user: SysUser, target_user_id: int) -> SysUser:
    target = db.query(SysUser).filter(SysUser.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    check_can_manage_user(db, current_user, target)
    return target


# ============================================================
# 用户 CRUD
# ============================================================

@router.get("")
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    agency_id: int | None = Query(default=None),
    role_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """用户列表：平台管理员看全部，机构管理员看本机构及下级机构用户。"""
    manageable_ids = get_manageable_agency_ids(db, current_user)

    query = db.query(SysUser)
    if manageable_ids is not None:
        query = query.filter(SysUser.agency_id.in_(manageable_ids))

    if agency_id is not None:
        require_agency_in_scope(db, current_user, agency_id)
        query = query.filter(SysUser.agency_id == agency_id)

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(SysUser.username.like(like), SysUser.real_name.like(like), SysUser.phone.like(like), SysUser.email.like(like)))

    if status:
        query = query.filter(SysUser.status == status)
    else:
        # 当前删除策略已改为物理删除；这里兼容过滤历史 archived 脏数据。
        query = query.filter(SysUser.status != "archived")

    if role_code:
        role_user_ids = (
            db.query(SysUserRoleBinding.user_id)
            .filter(SysUserRoleBinding.role_code == role_code, SysUserRoleBinding.status == "active")
            .distinct()
            .all()
        )
        query = query.filter(SysUser.id.in_([row[0] for row in role_user_ids]))

    total = query.count()
    items = (
        query.order_by(SysUser.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return success({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_user_to_dict(u, db) for u in items],
    })


@router.get("/{user_id}")
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    user = _require_user_scope(db, current_user, user_id)
    return success(_user_to_dict(user, db))


@router.post("")
def create_user(
    req: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """新增用户。"""
    if req.agency_id is None:
        if not is_platform_admin(db, current_user.id) and current_user.agency_id:
            req.agency_id = current_user.agency_id
        else:
            raise HTTPException(status_code=400, detail="请选择用户所属机构")

    require_agency_in_scope(db, current_user, req.agency_id)

    if db.query(SysUser).filter(SysUser.username == req.username).first():
        return fail(message=f"用户名 '{req.username}' 已存在", code=400)

    agency = db.query(Agency).filter(Agency.id == req.agency_id, Agency.status != "archived").first()
    if not agency:
        return fail(message="所属机构不存在或已删除", code=404)

    user = SysUser(
        username=req.username,
        password_hash=get_password_hash(req.password),
        real_name=req.real_name,
        phone=req.phone,
        email=req.email,
        agency_id=req.agency_id,
        status=req.status or "active",
    )
    db.add(user)
    db.flush()

    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="USER_CREATE",
        request=request,
        resource_type="user",
        resource_id=user.id,
        agency_id=user.agency_id,
    )
    anchor_resource_operation(
        db,
        resource_type="user",
        resource_id=user.id,
        operation_type="create",
        operator=current_user,
        agency_id=user.agency_id,
        before_data=None,
        after_data=user,
    )
    db.commit()
    db.refresh(user)
    return success(_user_to_dict(user, db))


@router.put("/{user_id}")
def update_user(
    user_id: int,
    req: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    user = _require_user_scope(db, current_user, user_id)
    before = object_to_dict(user)

    update_data = req.model_dump(exclude_unset=True)
    if "agency_id" in update_data and update_data["agency_id"] is not None:
        require_agency_in_scope(db, current_user, update_data["agency_id"])
        if not db.query(Agency).filter(Agency.id == update_data["agency_id"], Agency.status != "archived").first():
            return fail(message="所属机构不存在或已删除", code=404)

    for key, value in update_data.items():
        setattr(user, key, value)
    user.updated_at = datetime.now()
    db.flush()

    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="USER_UPDATE",
        request=request,
        resource_type="user",
        resource_id=user.id,
        agency_id=user.agency_id,
    )
    anchor_resource_operation(
        db,
        resource_type="user",
        resource_id=user.id,
        operation_type="update",
        operator=current_user,
        agency_id=user.agency_id,
        before_data=before,
        after_data=user,
    )
    db.commit()
    db.refresh(user)
    return success(_user_to_dict(user, db))


def _set_user_status(db: Session, user_id: int, status: str, current_user: SysUser, request: Request):
    if status not in {"active", "disabled"}:
        raise HTTPException(status_code=400, detail="用户状态只能是 active 或 disabled")

    if user_id == current_user.id and status == "disabled":
        return fail(message="不能禁用自己", code=400)

    user = _require_user_scope(db, current_user, user_id)

    if user.status == status:
        return success(_user_to_dict(user, db))

    before = object_to_dict(user)
    user.status = status
    user.updated_at = datetime.now()
    db.flush()

    operation_type_map = {
        "active": "USER_ENABLE",
        "disabled": "USER_DISABLE",
    }
    chain_operation_map = {
        "active": "enable",
        "disabled": "disable",
    }

    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type=operation_type_map[status],
        request=request,
        resource_type="user",
        resource_id=user.id,
        agency_id=user.agency_id,
    )
    anchor_resource_operation(
        db,
        resource_type="user",
        resource_id=user.id,
        operation_type=chain_operation_map[status],
        operator=current_user,
        agency_id=user.agency_id,
        before_data=before,
        after_data=user,
    )
    db.commit()
    db.refresh(user)
    return success(_user_to_dict(user, db))


@router.post("/{user_id}/enable")
def enable_user(user_id: int, request: Request, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    return _set_user_status(db, user_id, "active", current_user, request)


@router.post("/{user_id}/disable")
def disable_user_post(user_id: int, request: Request, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    return _set_user_status(db, user_id, "disabled", current_user, request)


@router.delete("/{user_id}")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    """物理删除用户：同步清理角色绑定、用户群组关系、操作日志和存证记录。"""
    if user_id == current_user.id:
        return fail(message="不能删除自己", code=400)

    user = _require_user_scope(db, current_user, user_id)

    try:
        _delete_chain_records(db, "user", [user.id])
        _delete_operate_logs(db, "user", [user.id])
        _delete_by_values(db, "sys_user_operate_log", "user_id", [user.id])
        _delete_by_values(db, "sys_user_role_binding", "user_id", [user.id])
        _delete_by_values(db, "sys_user_group", "user_id", [user.id])

        db.delete(user)
        db.commit()
        return success({"deleted": True, "user_id": user_id})
    except Exception:
        db.rollback()
        raise


# ============================================================
# 角色绑定
# ============================================================

@router.get("/{user_id}/roles")
def list_user_roles(user_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    _require_user_scope(db, current_user, user_id)
    bindings = (
        db.query(SysUserRoleBinding)
        .filter(SysUserRoleBinding.user_id == user_id)
        .order_by(SysUserRoleBinding.id.desc())
        .all()
    )
    return success([
        {
            "id": b.id,
            "user_id": b.user_id,
            "role_code": b.role_code,
            "scope_type": b.scope_type,
            "scope_id": b.scope_id,
            "status": b.status,
            "created_at": _format_dt(b.created_at),
        }
        for b in bindings
    ])


@router.post("/{user_id}/roles")
def bind_role(
    user_id: int,
    req: RoleBindRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    target_user = _require_user_scope(db, current_user, user_id)

    if req.role_code not in {"admin", "user", "governor"}:
        return fail(message="角色编码只能是 admin、user、governor", code=400)
    if req.scope_type not in {"platform", "agency", "group"}:
        return fail(message="作用域只能是 platform、agency、group", code=400)

    if req.scope_type == "platform":
        if not is_platform_admin(db, current_user.id):
            return fail(message="非平台管理员不能授权平台级角色", code=403)
        req.scope_id = None

    if req.scope_type == "agency":
        if req.scope_id is None:
            req.scope_id = target_user.agency_id
        require_agency_in_scope(db, current_user, req.scope_id)

    if req.scope_type == "group":
        if req.scope_id is None:
            return fail(message="群组角色必须指定 scope_id", code=400)
        if not is_platform_admin(db, current_user.id):
            check_group_admin_access(db, current_user.id, req.scope_id)

    exists = db.query(SysUserRoleBinding).filter(
        SysUserRoleBinding.user_id == user_id,
        SysUserRoleBinding.role_code == req.role_code,
        SysUserRoleBinding.scope_type == req.scope_type,
        SysUserRoleBinding.scope_id == req.scope_id,
        SysUserRoleBinding.status == "active",
    ).first()
    if exists:
        return fail(message="该角色绑定已存在", code=400)

    disabled_binding = db.query(SysUserRoleBinding).filter(
        SysUserRoleBinding.user_id == user_id,
        SysUserRoleBinding.role_code == req.role_code,
        SysUserRoleBinding.scope_type == req.scope_type,
        SysUserRoleBinding.scope_id == req.scope_id,
        SysUserRoleBinding.status == "disabled",
    ).first()

    before = None
    if disabled_binding:
        before = object_to_dict(disabled_binding)
        disabled_binding.status = "active"
        disabled_binding.created_by = current_user.id
        disabled_binding.disabled_at = None
        binding = disabled_binding
    else:
        binding = SysUserRoleBinding(
            user_id=user_id,
            role_code=req.role_code,
            scope_type=req.scope_type,
            scope_id=req.scope_id,
            status="active",
            created_by=current_user.id,
        )
        db.add(binding)
    db.flush()

    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="ROLE_BIND",
        request=request,
        resource_type="user_role",
        resource_id=binding.id,
        agency_id=target_user.agency_id,
    )
    anchor_resource_operation(
        db,
        resource_type="role_binding",
        resource_id=binding.id,
        operation_type="assign_role",
        operator=current_user,
        agency_id=target_user.agency_id,
        before_data=before,
        after_data=binding,
    )
    db.commit()
    db.refresh(binding)

    return success({
        "id": binding.id,
        "user_id": binding.user_id,
        "role_code": binding.role_code,
        "scope_type": binding.scope_type,
        "scope_id": binding.scope_id,
        "status": binding.status,
    })


@router.delete("/{user_id}/roles/{binding_id}")
def unbind_role(
    user_id: int,
    binding_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    target_user = _require_user_scope(db, current_user, user_id)
    binding = db.query(SysUserRoleBinding).filter(
        SysUserRoleBinding.id == binding_id,
        SysUserRoleBinding.user_id == user_id,
        SysUserRoleBinding.status == "active",
    ).first()
    if not binding:
        return fail(message="角色绑定不存在", code=404)

    if binding.scope_type == "platform" and not is_platform_admin(db, current_user.id):
        return fail(message="非平台管理员不能取消平台级角色", code=403)
    if binding.scope_type == "agency" and binding.scope_id:
        require_agency_in_scope(db, current_user, binding.scope_id)
    if binding.scope_type == "group" and binding.scope_id and not is_platform_admin(db, current_user.id):
        check_group_admin_access(db, current_user.id, binding.scope_id)

    if binding.role_code == "admin" and binding.scope_type == "group" and binding.scope_id:
        other_admins = db.query(SysUserRoleBinding).filter(
            SysUserRoleBinding.user_id != user_id,
            SysUserRoleBinding.role_code == "admin",
            SysUserRoleBinding.scope_type == "group",
            SysUserRoleBinding.scope_id == binding.scope_id,
            SysUserRoleBinding.status == "active",
        ).count()
        if other_admins == 0:
            return fail(message="不能取消该群组的最后一个管理员", code=400)

    before = object_to_dict(binding)
    binding.status = "disabled"
    binding.disabled_at = datetime.now()
    db.flush()

    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="ROLE_UNBIND",
        request=request,
        resource_type="user_role",
        resource_id=binding_id,
        agency_id=target_user.agency_id,
    )
    anchor_resource_operation(
        db,
        resource_type="role_binding",
        resource_id=binding.id,
        operation_type="remove_role",
        operator=current_user,
        agency_id=target_user.agency_id,
        before_data=before,
        after_data=binding,
    )
    db.commit()
    return success({"disabled": True, "binding_id": binding_id})


# ============================================================
# 群组绑定（保留旧功能）
# ============================================================

@router.get("/{user_id}/groups")
def list_user_groups(user_id: int, db: Session = Depends(get_db), current_user: SysUser = Depends(get_current_user)):
    _require_user_scope(db, current_user, user_id)
    user_groups = db.query(SysUserGroup).filter(SysUserGroup.user_id == user_id).order_by(SysUserGroup.id.desc()).all()
    result = []
    for ug in user_groups:
        group_name = None
        gi = db.query(GroupInfo).filter(GroupInfo.id == ug.group_id).first()
        if gi:
            group_name = gi.group_name
        result.append({
            "id": ug.id,
            "user_id": ug.user_id,
            "group_id": ug.group_id,
            "group_name": group_name,
            "agency_id": ug.agency_id,
            "join_status": ug.join_status,
            "created_at": _format_dt(ug.created_at),
        })
    return success(result)


@router.post("/{user_id}/groups")
def add_user_to_group(
    user_id: int,
    req: GroupBindRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    target_user = _require_user_scope(db, current_user, user_id)
    group = db.query(GroupInfo).filter(GroupInfo.id == req.group_id).first()
    if not group:
        return fail(message="群组不存在", code=404)

    if not is_platform_admin(db, current_user.id):
        check_group_admin_access(db, current_user.id, req.group_id)

    agency_id = req.agency_id or target_user.agency_id
    if agency_id:
        member = db.query(GroupMember).filter(
            GroupMember.group_id == req.group_id,
            GroupMember.agency_id == agency_id,
            GroupMember.join_status == "active",
        ).first()
        if not member:
            return fail(message="用户所属机构不是该群组的成员机构", code=400)

    exists = db.query(SysUserGroup).filter(
        SysUserGroup.user_id == user_id,
        SysUserGroup.group_id == req.group_id,
        SysUserGroup.join_status == "active",
    ).first()
    if exists:
        return fail(message="用户已在该群组中", code=400)

    disabled = db.query(SysUserGroup).filter(
        SysUserGroup.user_id == user_id,
        SysUserGroup.group_id == req.group_id,
        SysUserGroup.join_status == "disabled",
    ).first()
    if disabled:
        ug = disabled
        ug.join_status = "active"
        ug.disabled_at = None
        ug.authorized_by = current_user.id
        ug.authorized_at = datetime.now()
        ug.agency_id = agency_id
    else:
        ug = SysUserGroup(
            user_id=user_id,
            group_id=req.group_id,
            agency_id=agency_id,
            join_status="active",
            authorized_by=current_user.id,
            authorized_at=datetime.now(),
        )
        db.add(ug)
    db.flush()

    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="USER_ADD_GROUP",
        request=request,
        resource_type="user_group",
        resource_id=ug.id,
        group_id=req.group_id,
        agency_id=agency_id,
    )
    db.commit()
    return success({"id": ug.id, "user_id": ug.user_id, "group_id": ug.group_id, "join_status": ug.join_status})


@router.delete("/{user_id}/groups/{group_id}")
def remove_user_from_group(
    user_id: int,
    group_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _require_user_scope(db, current_user, user_id)
    ug = db.query(SysUserGroup).filter(
        SysUserGroup.user_id == user_id,
        SysUserGroup.group_id == group_id,
        SysUserGroup.join_status == "active",
    ).first()
    if not ug:
        return fail(message="用户群组关系不存在", code=404)

    if not is_platform_admin(db, current_user.id):
        check_group_admin_access(db, current_user.id, group_id)

    ug.join_status = "disabled"
    ug.disabled_at = datetime.now()
    db.flush()

    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="USER_REMOVE_GROUP",
        request=request,
        resource_type="user_group",
        resource_id=ug.id,
        group_id=group_id,
        agency_id=ug.agency_id,
    )
    db.commit()
    return success({"disabled": True, "user_group_id": ug.id})
