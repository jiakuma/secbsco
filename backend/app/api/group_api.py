"""
群组管理 API。

接口列表：
- GET    /api/groups                              群组列表
- POST   /api/groups                              创建群组
- GET    /api/groups/{group_id}                   群组详情
- PUT    /api/groups/{group_id}                   编辑群组基础信息
- POST   /api/groups/{group_id}/approve           审批通过
- POST   /api/groups/{group_id}/reject            驳回
- GET    /api/groups/{group_id}/lifecycle-logs     生命周期日志
- GET    /api/groups/{group_id}/members            成员机构列表
- POST   /api/groups/{group_id}/members            添加成员机构
- DELETE /api/groups/{group_id}/members/{agency_id} 移除成员机构
- GET    /api/groups/{group_id}/users              群组用户列表
- POST   /api/groups/{group_id}/users              添加群组用户
- PUT    /api/groups/{group_id}/users/{user_id}/role  修改用户角色
- DELETE /api/groups/{group_id}/users/{user_id}    移出群组用户
- GET    /api/groups/{group_id}/nodes              已授权节点列表
- GET    /api/groups/{group_id}/available-nodes    可授权节点列表
- POST   /api/groups/{group_id}/nodes              授权节点
- DELETE /api/groups/{group_id}/nodes/{node_id}    取消节点授权
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.schemas.group_schema import (
    GroupCreate, GroupUpdate, GroupApprove, GroupReject,
    AddGroupMember, AddGroupUser, UpdateGroupUserRole, AddGroupNode,
)
from app.services import group_service, group_lifecycle_service
from app.utils.response import success, fail

router = APIRouter(prefix="/api/groups", tags=["群组管理"])


# ============================================================
# 用户可见群组（用于任务管理下拉）
# ============================================================

@router.get("/visible-for-task")
def get_visible_groups_for_task(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """
    获取当前用户可见群组列表（用于任务管理下拉菜单）。

    权限规则：
    - 平台管理员：可见全部群组
    - 机构管理员：可见本机构及下辖机构参与的群组
    - 业务用户：可见自己所属机构参与的群组
    """
    try:
        from app.services.access_control_service import (
            is_platform_admin,
            is_agency_admin,
        )
        from app.models.group import GroupInfo, GroupMember
        from app.models.agency import Agency

        if is_platform_admin(db, current_user.id):
            groups = db.query(GroupInfo).filter(GroupInfo.status == "active").order_by(GroupInfo.id.desc()).all()
        else:
            user_agency_id = current_user.agency_id
            if not user_agency_id:
                return success(data=[])

            agency_ids = [user_agency_id]
            if is_agency_admin(db, current_user.id):
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

            group_ids = (
                db.query(GroupMember.group_id)
                .filter(
                    GroupMember.agency_id.in_(agency_ids),
                    GroupMember.join_status == "active",
                )
                .distinct()
                .all()
            )
            group_id_list = [g[0] for g in group_ids]

            groups = (
                db.query(GroupInfo)
                .filter(
                    GroupInfo.id.in_(group_id_list),
                    GroupInfo.status == "active",
                )
                .order_by(GroupInfo.id.desc())
                .all()
            )

        return success(data=[
            {"id": g.id, "group_name": g.group_name, "group_code": g.group_code}
            for g in groups
        ])
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组列表
# ============================================================

@router.get("")
def get_group_list(
    keyword: str | None = Query(default=None, description="按群组编码/名称模糊查询"),
    status: str | None = Query(default=None, description="按群组状态过滤"),
    region_code: str | None = Query(default=None, description="按区域编码过滤"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询群组列表（权限过滤 + 分页）。"""
    try:
        data = group_service.list_groups(
            db, current_user, keyword=keyword, status=status,
            region_code=region_code, page=page, page_size=page_size,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 创建群组
# ============================================================

@router.post("")
def create_group(
    payload: GroupCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """创建群组（自动判断权限、审批逻辑、绑定创建人）。"""
    try:
        data = group_service.create_group_with_creator_admin(
            db, payload.model_dump(exclude_unset=True), current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组详情
# ============================================================

@router.get("/{group_id}")
def get_group_detail(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取群组详情 + 统计摘要。"""
    try:
        data = group_service.get_group_detail(db, group_id, current_user)
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 编辑群组基础信息
# ============================================================

@router.put("/{group_id}")
def update_group(
    group_id: int,
    payload: GroupUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """编辑群组基础信息。"""
    try:
        data = group_service.update_group_basic_info(
            db, group_id, payload.model_dump(exclude_unset=True), current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 审批通过
# ============================================================

@router.post("/{group_id}/approve")
def approve_group(
    group_id: int,
    payload: GroupApprove,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """审批通过群组。"""
    try:
        data = group_service.approve_group(
            db, group_id, payload.model_dump(exclude_unset=True), current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 驳回
# ============================================================

@router.post("/{group_id}/reject")
def reject_group(
    group_id: int,
    payload: GroupReject,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """驳回群组申请。"""
    try:
        data = group_service.reject_group(
            db, group_id, payload.model_dump(exclude_unset=True), current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 生命周期日志
# ============================================================

@router.get("/{group_id}/lifecycle-logs")
def get_lifecycle_logs(
    group_id: int,
    event_type: str | None = Query(default=None, description="事件类型过滤"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询群组生命周期日志。"""
    try:
        data = group_lifecycle_service.list_lifecycle_logs(
            db, group_id, event_type=event_type, page=page, page_size=page_size,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 成员机构 - 列表
# ============================================================

@router.get("/{group_id}/members")
def get_group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询群组成员机构。"""
    try:
        data = group_service.list_group_members(db, group_id, current_user)
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 成员机构 - 添加
# ============================================================

@router.post("/{group_id}/members")
def add_group_member(
    group_id: int,
    payload: AddGroupMember,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """添加成员机构。"""
    try:
        data = group_service.add_group_member(
            db, group_id, payload.model_dump(exclude_unset=True), current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 成员机构 - 移除
# ============================================================

@router.delete("/{group_id}/members/{agency_id}")
def remove_group_member(
    group_id: int,
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """移除成员机构。"""
    try:
        data = group_service.remove_group_member(
            db, group_id, agency_id, current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组用户 - 列表
# ============================================================

@router.get("/{group_id}/users")
def get_group_users(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询群组用户及其群组角色。"""
    try:
        data = group_service.list_group_users(db, group_id, current_user)
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组用户 - 添加
# ============================================================

@router.post("/{group_id}/users")
def add_group_user(
    group_id: int,
    payload: AddGroupUser,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """添加群组用户并授权角色。"""
    try:
        data = group_service.add_group_user(
            db, group_id, payload.model_dump(exclude_unset=True), current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组用户 - 修改角色
# ============================================================

@router.put("/{group_id}/users/{user_id}/role")
def update_group_user_role(
    group_id: int,
    user_id: int,
    payload: UpdateGroupUserRole,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """修改用户在群组内的角色。"""
    try:
        data = group_service.update_group_user_role(
            db, group_id, user_id, payload.model_dump(exclude_unset=True), current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组用户 - 移出
# ============================================================

@router.delete("/{group_id}/users/{user_id}")
def remove_group_user(
    group_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """将用户移出群组。"""
    try:
        data = group_service.remove_group_user(
            db, group_id, user_id, current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组节点 - 已授权列表
# ============================================================

@router.get("/{group_id}/nodes")
def get_group_nodes(
    group_id: int,
    node_type: str | None = Query(default=None, description="节点类型过滤"),
    node_usage_role: str | None = Query(default=None, description="节点用途角色过滤"),
    auth_status: str | None = Query(default=None, description="授权状态过滤"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询群组已授权节点。"""
    try:
        data = group_service.list_group_nodes(
            db, group_id, current_user,
            node_type=node_type, node_usage_role=node_usage_role, auth_status=auth_status,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组节点 - 可授权列表
# ============================================================

@router.get("/{group_id}/available-nodes")
def get_available_group_nodes(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """查询群组可授权节点列表（来自成员机构）。"""
    try:
        data = group_service.list_available_group_nodes(db, group_id, current_user)
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组节点 - 授权
# ============================================================

@router.post("/{group_id}/nodes")
def add_group_node(
    group_id: int,
    payload: AddGroupNode,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """授权节点给群组。"""
    try:
        data = group_service.add_group_node(
            db, group_id, payload.model_dump(exclude_unset=True), current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组节点 - 取消授权
# ============================================================

@router.delete("/{group_id}/nodes/{node_id}")
def remove_group_node(
    group_id: int,
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """取消群组节点授权。"""
    try:
        data = group_service.remove_group_node(
            db, group_id, node_id, current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组删除 - 申请删除
# ============================================================

@router.post("/{group_id}/delete-request")
def request_delete_group(
    group_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """申请删除群组（平台管理员或上级直接删除，同级协作需审批）。"""
    try:
        data = group_service.request_delete_group(
            db, group_id, current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组删除 - 审批通过
# ============================================================

@router.post("/{group_id}/delete-approve")
def approve_delete_group(
    group_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """审批通过删除群组，执行物理删除。"""
    try:
        data = group_service.approve_delete_group(
            db, group_id, current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组删除 - 审批驳回
# ============================================================

@router.post("/{group_id}/delete-reject")
def reject_delete_group(
    group_id: int,
    payload: GroupReject,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """驳回删除群组申请。"""
    try:
        data = group_service.reject_delete_group(
            db, group_id, payload.reason, current_user, request,
        )
        return success(data=data)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)
