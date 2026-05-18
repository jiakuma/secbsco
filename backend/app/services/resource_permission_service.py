"""
第5阶段：基础资源管理权限服务。

核心原则：
- 平台管理员管理全部机构、用户、节点。
- 机构管理员管理本机构及下级机构的机构、用户、节点。
- 群组管理员、业务用户、治理员不进入基础资源管理。
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.agency import Agency
from app.models.sys_user import SysUser
from app.models.node import Node
from app.services.access_control_service import is_platform_admin, has_role


AGENCY_LEVEL_ORDER = {
    "national": 1,
    "province": 2,
    "city": 3,
    "county": 4,
}


def is_base_resource_admin(db: Session, user: SysUser) -> bool:
    """是否具备基础资源管理入口权限。"""
    if is_platform_admin(db, user.id):
        return True
    return has_role(db, user.id, "admin", "agency")


def require_base_resource_admin(db: Session, user: SysUser) -> None:
    """校验基础资源管理权限。"""
    if not is_base_resource_admin(db, user):
        raise HTTPException(status_code=403, detail="需要平台管理员或机构管理员权限")


def get_descendant_agency_ids(db: Session, root_agency_id: int, include_self: bool = True) -> list[int]:
    """获取某机构及其所有下级机构 ID。"""
    result: list[int] = []
    visited: set[int] = set()
    queue: list[int] = [root_agency_id]

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        if include_self or current_id != root_agency_id:
            result.append(current_id)

        children = (
            db.query(Agency.id)
            .filter(
                Agency.parent_agency_id == current_id,
                Agency.status != "archived",
            )
            .all()
        )
        queue.extend([row[0] for row in children])

    return result


def get_self_and_descendant_agency_ids(db: Session, root_agency_id: int) -> list[int]:
    """获取当前机构及所有下辖机构 ID。用于机构管理员的基础资源管理范围。"""
    return get_descendant_agency_ids(db, root_agency_id, include_self=True)


def get_manageable_agency_ids(db: Session, user: SysUser) -> list[int] | None:
    """
    返回当前用户可管理机构范围。

    - platform admin 返回 None，表示全量管理。
    - agency admin 返回本机构及下级机构 ID。
    - 其他用户抛出 403。
    """
    if is_platform_admin(db, user.id):
        return None

    if not has_role(db, user.id, "admin", "agency"):
        raise HTTPException(status_code=403, detail="需要机构管理员权限")

    # 优先使用用户所属机构。若历史数据中 role binding scope_id 更准确，也合并处理。
    root_ids: set[int] = set()
    if user.agency_id:
        root_ids.add(user.agency_id)

    from app.models.user import SysUserRoleBinding

    bindings = (
        db.query(SysUserRoleBinding)
        .filter(
            SysUserRoleBinding.user_id == user.id,
            SysUserRoleBinding.role_code == "admin",
            SysUserRoleBinding.scope_type == "agency",
            SysUserRoleBinding.status == "active",
        )
        .all()
    )
    for binding in bindings:
        if binding.scope_id:
            root_ids.add(binding.scope_id)

    if not root_ids:
        raise HTTPException(status_code=403, detail="当前机构管理员未绑定机构范围")

    manageable_ids: set[int] = set()
    for root_id in root_ids:
        manageable_ids.update(get_descendant_agency_ids(db, root_id, include_self=True))

    return sorted(manageable_ids)


def is_agency_in_scope(db: Session, user: SysUser, agency_id: int | None) -> bool:
    """判断 agency_id 是否在当前用户管理范围内。"""
    if agency_id is None:
        return False

    ids = get_manageable_agency_ids(db, user)
    if ids is None:
        return True
    return agency_id in ids


def require_agency_in_scope(db: Session, user: SysUser, agency_id: int | None) -> None:
    if not is_agency_in_scope(db, user, agency_id):
        raise HTTPException(status_code=403, detail="无权管理该机构范围内的资源")


def get_agency_query_scope(db: Session, user: SysUser):
    """返回 SQLAlchemy 查询过滤条件所需的可管理机构 ID。"""
    return get_manageable_agency_ids(db, user)


def _get_current_admin_agency(db: Session, user: SysUser) -> Agency:
    """获取机构管理员自身所属机构，用于判断其可创建的下级层级。"""
    if not user.agency_id:
        raise HTTPException(status_code=403, detail="当前机构管理员未绑定所属机构")

    agency = db.query(Agency).filter(Agency.id == user.agency_id).first()
    if not agency:
        raise HTTPException(status_code=403, detail="当前机构管理员所属机构不存在")
    return agency


def _require_valid_agency_level(level: str | None) -> int:
    """校验机构层级并返回排序值。"""
    order = AGENCY_LEVEL_ORDER.get(level or "")
    if order is None:
        raise HTTPException(status_code=400, detail="机构层级只能是 national、province、city、county")
    return order


def check_can_create_child_agency(db: Session, user: SysUser, parent_agency_id: int | None, child_level: str | None = None) -> None:
    """
    校验是否可新增机构。

    新规则：
    - 平台管理员可创建任意层级机构，但仍要满足行政层级顺序；
    - 非平台管理员只能在自身权限范围内创建下级机构；
    - 非平台管理员不能创建同级机构或上级机构；
    - 非平台管理员不能选择权限范围外的上级机构。
    """
    child_order = _require_valid_agency_level(child_level)

    if parent_agency_id is None:
        if is_platform_admin(db, user.id) and child_level == "national":
            return
        raise HTTPException(status_code=403, detail="机构管理员只能创建下级机构，不能创建同级或上级机构")

    parent = db.query(Agency).filter(Agency.id == parent_agency_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="上级机构不存在")

    parent_order = _require_valid_agency_level(parent.agency_level)
    if child_order <= parent_order:
        raise HTTPException(status_code=400, detail="新增机构层级必须低于上级机构层级")

    if is_platform_admin(db, user.id):
        return

    require_agency_in_scope(db, user, parent_agency_id)

    current_agency = _get_current_admin_agency(db, user)
    current_order = _require_valid_agency_level(current_agency.agency_level)
    if child_order <= current_order:
        raise HTTPException(status_code=400, detail="机构管理员只能创建下级机构，不能创建同级或上级机构")


def check_can_manage_agency(db: Session, user: SysUser, agency_id: int) -> None:
    require_agency_in_scope(db, user, agency_id)


def check_can_manage_user(db: Session, user: SysUser, target_user: SysUser) -> None:
    require_agency_in_scope(db, user, target_user.agency_id)


def check_can_manage_node(db: Session, user: SysUser, node: Node) -> None:
    require_agency_in_scope(db, user, node.agency_id)
