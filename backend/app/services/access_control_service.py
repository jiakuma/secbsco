"""
访问控制服务：用户上下文、角色判断、权限校验。

核心方法：
- get_user_context: 获取用户完整上下文
- get_accessible_group_ids: 获取可访问群组 ID 列表
- has_role: 判断角色
- check_group_access / check_group_admin_access / check_governor_group_access: 权限校验
- build_permissions: 根据角色+作用域生成权限列表
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.sys_user import SysUser
from app.models.agency import Agency
from app.models.user import (
    SysUserRoleBinding,
    SysUserGroup,
    SysUserOperateLog,
)
from app.models.group import GroupInfo, GroupMember


# ============================================================
# 角色权限定义
# ============================================================

# 角色 + 作用域 → 权限列表
ROLE_PERMISSIONS = {
    # admin + platform = 平台管理员
    ("admin", "platform"): [
        "dashboard:read",
        "task:read", "task:create", "task:update", "task:delete", "task:run",
        "task_result:read",
        "agency:read", "agency:create", "agency:update",
        "node:read", "node:create", "node:update",
        "group:read", "group:create", "group:update", "group:delete",
        "user:read", "user:create", "user:update", "user:delete",
        "role:read", "role:grant", "role:revoke",
        "audit_log:read",
        "chain_record:read",
        "stat_template:read", "stat_template:create",
    ],
    # admin + agency = 机构管理员
    ("admin", "agency"): [
        "dashboard:read",
        "task:read", "task:create", "task:update", "task:run",
        "task_result:read",
        "agency:read",
        "node:read",
        "group:read", "group:create", "group:update",
        "user:read", "user:create", "user:update",
        "role:read",
        "audit_log:read",
        "stat_template:read",
    ],
    # admin + group = 群组管理员
    ("admin", "group"): [
        "dashboard:read",
        "task:read", "task:create", "task:update", "task:run",
        "task_result:read",
        "group:read", "group:update", "group:manage",
        "node:read",
        "user:read", "user:create", "user:update",
        "role:read",
        "audit_log:read",
        "stat_template:read", "stat_template:create",
    ],
    # user + group = 群组业务用户
    ("user", "group"): [
        "dashboard:read",
        "task:read", "task:create", "task:run",
        "task_result:read",
        "group:read",
        "audit_log:read",
        "stat_template:read",
    ],
    # governor + group = 群组区块链治理员
    ("governor", "group"): [
        "dashboard:read",
        "task_result:read",
        "chain_record:read", "chain_record:verify",
        "contract:read",
        "audit_log:read",
    ],
}


def build_permissions(role_bindings: list[dict]) -> list[str]:
    """
    根据角色绑定列表生成去重权限列表。

    Args:
        role_bindings: [{"role_code": "admin", "scope_type": "group", "scope_id": 1}, ...]
    """
    permissions = set()
    for rb in role_bindings:
        key = (rb["role_code"], rb["scope_type"])
        perms = ROLE_PERMISSIONS.get(key, [])
        permissions.update(perms)
    return sorted(permissions)


def has_permission(permissions: list[str], permission: str) -> bool:
    """判断权限列表中是否包含指定权限。"""
    return permission in permissions


# ============================================================
# 用户上下文
# ============================================================

def get_user_context(db: Session, user_id: int) -> dict:
    """
    获取用户完整上下文。

    Returns:
        {
            "user": SysUser,
            "agency": Agency | None,
            "agency_name": str | None,
            "groups": [{"group_id": int, "group_code": str, "group_name": str, "status": str}],
            "roles": [{"role_code": str, "scope_type": str, "scope_id": int | None}],
            "permissions": [str],
            "current_group_id": int | None,
        }
    """
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    # 关联机构
    agency_name = None
    agency = None
    if user.agency_id:
        agency = db.query(Agency).filter(Agency.id == user.agency_id).first()
        if agency:
            agency_name = agency.agency_name

    # 用户群组
    user_groups = (
        db.query(SysUserGroup)
        .filter(
            SysUserGroup.user_id == user_id,
            SysUserGroup.join_status == "active",
        )
        .all()
    )

    groups = []
    for ug in user_groups:
        gi = db.query(GroupInfo).filter(GroupInfo.id == ug.group_id).first()
        if gi:
            groups.append({
                "group_id": gi.id,
                "group_code": gi.group_code,
                "group_name": gi.group_name,
                "status": gi.status,
            })

    # 用户角色
    role_bindings = (
        db.query(SysUserRoleBinding)
        .filter(
            SysUserRoleBinding.user_id == user_id,
            SysUserRoleBinding.status == "active",
        )
        .all()
    )

    roles = []
    for rb in role_bindings:
        roles.append({
            "role_code": rb.role_code,
            "scope_type": rb.scope_type,
            "scope_id": rb.scope_id,
        })

    # 生成权限
    permissions = build_permissions(roles)

    # 默认群组
    current_group_id = None
    for g in groups:
        if g["status"] == "active":
            current_group_id = g["group_id"]
            break

    # platform admin 不强制 current_group_id
    is_platform_admin = any(
        r["role_code"] == "admin" and r["scope_type"] == "platform"
        for r in roles
    )

    return {
        "user": user,
        "agency": agency,
        "agency_name": agency_name,
        "groups": groups,
        "roles": roles,
        "permissions": permissions,
        "current_group_id": current_group_id if not is_platform_admin else None,
        "is_platform_admin": is_platform_admin,
    }


def get_accessible_group_ids(db: Session, user_id: int) -> list[int] | None:
    """
    获取用户可访问的 group_id 列表。

    - platform admin 返回 None（代表全局可访问）
    - 其他用户返回其加入的群组 ID 列表（不限状态，因为 draft/configuring 状态的创建人仍需访问）
    """
    user_ctx = get_user_context(db, user_id)

    if user_ctx["is_platform_admin"]:
        return None  # 全局可访问

    return [g["group_id"] for g in user_ctx["groups"]]


# ============================================================
# 角色判断
# ============================================================

def has_role(
    db: Session,
    user_id: int,
    role_code: str,
    scope_type: str | None = None,
    scope_id: int | None = None,
) -> bool:
    """判断用户是否拥有指定角色。"""
    query = (
        db.query(SysUserRoleBinding)
        .filter(
            SysUserRoleBinding.user_id == user_id,
            SysUserRoleBinding.role_code == role_code,
            SysUserRoleBinding.status == "active",
        )
    )

    if scope_type is not None:
        query = query.filter(SysUserRoleBinding.scope_type == scope_type)

    if scope_id is not None:
        query = query.filter(SysUserRoleBinding.scope_id == scope_id)

    return query.first() is not None


def is_admin(db: Session, user_id: int) -> bool:
    """判断用户是否为任意级别的 admin。"""
    return has_role(db, user_id, "admin")


def is_platform_admin(db: Session, user_id: int) -> bool:
    """判断用户是否为 platform admin。"""
    return has_role(db, user_id, "admin", "platform")


def is_governor(db: Session, user_id: int, group_id: int) -> bool:
    """判断用户是否为某群组的 governor。"""
    return has_role(db, user_id, "governor", "group", group_id)


# ============================================================
# 权限校验（带异常抛出）
# ============================================================

def check_admin_access(db: Session, user_id: int) -> None:
    """校验用户是否为 admin，否则抛出 403。"""
    if not is_admin(db, user_id):
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限",
        )


def check_group_access(db: Session, user_id: int, group_id: int) -> None:
    """
    校验用户是否可访问某群组，无权限抛出 404（避免暴露资源存在性）。
    """
    accessible = get_accessible_group_ids(db, user_id)
    if accessible is not None and group_id not in accessible:
        raise HTTPException(status_code=404, detail="资源不存在或无权访问")


def check_group_admin_access(db: Session, user_id: int, group_id: int) -> None:
    """校验用户是否为某群组 admin 或 platform admin。"""
    if is_platform_admin(db, user_id):
        return

    if not has_role(db, user_id, "admin", "group", group_id):
        raise HTTPException(
            status_code=403,
            detail="需要群组管理员权限",
        )


def check_governor_group_access(db: Session, user_id: int, group_id: int) -> None:
    """校验用户是否为某群组 governor。"""
    if not is_governor(db, user_id, group_id):
        raise HTTPException(
            status_code=403,
            detail="需要区块链治理员权限",
        )


def check_task_run_access(db: Session, user_id: int, group_id: int | None = None) -> None:
    """
    校验用户是否可以执行任务。
    - governor 不可执行任务
    - 非群组成员不可执行任务
    """
    # governor 不可执行
    governor_bindings = (
        db.query(SysUserRoleBinding)
        .filter(
            SysUserRoleBinding.user_id == user_id,
            SysUserRoleBinding.role_code == "governor",
            SysUserRoleBinding.status == "active",
        )
        .all()
    )
    if governor_bindings:
        raise HTTPException(
            status_code=403,
            detail="区块链治理员不允许执行任务",
        )

    # platform admin 可执行
    if is_platform_admin(db, user_id):
        return

    # 需要是 admin 或 user 且在群组内
    if not is_admin(db, user_id) and not has_role(db, user_id, "user"):
        raise HTTPException(
            status_code=403,
            detail="需要业务用户或管理员权限才能执行任务",
        )

    # 有 group_id 时校验群组权限
    if group_id:
        check_group_access(db, user_id, group_id)


# ============================================================
# 操作日志
# ============================================================

def write_operate_log(
    db: Session,
    user_id: int | None = None,
    username: str | None = None,
    operation_type: str | None = None,
    request=None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    group_id: int | None = None,
    agency_id: int | None = None,
    request_path: str | None = None,
    request_method: str | None = None,
    request_params: dict | None = None,
    result_status: str = "success",
    ip_address: str | None = None,
    **kwargs,
) -> None:
    """写入操作日志。"""

    # 如果外部没有显式传 ip_address，则尝试从 request 中获取
    if not ip_address and request and hasattr(request, "client") and request.client:
        ip_address = request.client.host

    # 如果外部没有显式传 request_path / request_method，则尝试从 request 中获取
    if request and hasattr(request, "scope"):
        if not request_path:
            request_path = request.scope.get("path")
        if not request_method:
            request_method = request.scope.get("method")

    log = SysUserOperateLog(
        user_id=user_id,
        username=username,
        operation_type=operation_type,
        resource_type=resource_type,
        resource_id=resource_id,
        group_id=group_id,
        agency_id=agency_id,
        request_path=request_path,
        request_method=request_method,
        request_params=request_params,
        result_status=result_status,
        ip_address=ip_address,
    )

    db.add(log)
    db.flush()


# ============================================================
# 第4阶段新增：机构层级判断
# ============================================================

def is_agency_admin(db: Session, user_id: int, agency_id: int | None = None) -> bool:
    """
    判断用户是否为指定机构的机构管理员。
    如果未指定 agency_id，则判断用户是否为其所属机构的机构管理员。
    """
    if agency_id is None:
        user = db.query(SysUser).filter(SysUser.id == user_id).first()
        if not user:
            return False
        agency_id = user.agency_id
    if not agency_id:
        return False
    return has_role(db, user_id, "admin", "agency", agency_id)


def is_group_admin(db: Session, user_id: int, group_id: int) -> bool:
    """判断用户是否为某群组的群组管理员。"""
    return has_role(db, user_id, "admin", "group", group_id)


def is_ancestor_agency(db: Session, parent_agency_id: int, child_agency_id: int) -> bool:
    """
    判断 parent_agency 是否为 child_agency 的上级机构。
    沿 child_agency.parent_agency_id 向上递归查找。
    """
    current_id = child_agency_id
    visited = set()
    max_depth = 20  # 防止无限循环

    while current_id and current_id not in visited and max_depth > 0:
        if current_id == parent_agency_id:
            return True
        visited.add(current_id)
        max_depth -= 1
        agency = db.query(Agency).filter(Agency.id == current_id).first()
        if not agency:
            break
        current_id = agency.parent_agency_id

    return False


def is_same_level_agency(db: Session, agency_id_1: int, agency_id_2: int) -> bool:
    """
    判断两个机构是否同级（agency_level 相同，id 不同）。
    """
    if agency_id_1 == agency_id_2:
        return False
    a1 = db.query(Agency).filter(Agency.id == agency_id_1).first()
    a2 = db.query(Agency).filter(Agency.id == agency_id_2).first()
    if not a1 or not a2:
        return False
    return a1.agency_level == a2.agency_level and a1.agency_level is not None


def find_common_parent_agency(db: Session, agency_ids: list[int]) -> int | None:
    """
    查找多个机构的共同上级机构 ID。
    简化规则：如果所有机构 parent_id 相同，则共同上级 = 这个 parent_id。
    否则返回 None（由平台管理员审批）。
    """
    if not agency_ids:
        return None

    parent_ids = set()
    for aid in agency_ids:
        agency = db.query(Agency).filter(Agency.id == aid).first()
        if not agency:
            return None
        parent_ids.add(agency.parent_agency_id)

    if len(parent_ids) == 1 and None not in parent_ids:
        return parent_ids.pop()

    return None


def can_approve_group(db: Session, user_id: int, group: GroupInfo) -> bool:
    """
    判断用户是否有权审批指定群组。
    - 平台管理员可以审批全部
    - 如果 group.approval_agency_id 不为空，则该机构的机构管理员可以审批
    """
    if is_platform_admin(db, user_id):
        return True
    if group.approval_agency_id:
        return is_agency_admin(db, user_id, group.approval_agency_id)
    return False