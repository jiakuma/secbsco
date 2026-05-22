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


# ============================================================
# 群组数据集授权
# ============================================================

@router.get("/{group_id}/datasets")
def list_group_datasets(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取群组已授权数据集列表"""
    try:
        from app.models.group import GroupDataset
        from app.models.dataset import Dataset
        from app.services.access_control_service import check_group_access

        check_group_access(db, current_user.id, group_id)

        group_datasets = db.query(GroupDataset).filter(
            GroupDataset.group_id == group_id,
            GroupDataset.auth_status == "active",
        ).all()

        items = []
        for gd in group_datasets:
            dataset = db.query(Dataset).filter(Dataset.id == gd.dataset_id).first()
            if dataset:
                from app.models.agency import Agency
                agency = db.query(Agency).filter(Agency.id == dataset.agency_id).first()
                items.append({
                    "id": gd.id,
                    "dataset_id": dataset.id,
                    "dataset_name": dataset.dataset_name,
                    "dataset_code": dataset.dataset_code,
                    "agency_id": dataset.agency_id,
                    "agency_name": agency.agency_name if agency else None,
                    "node_id": dataset.node_id,
                    "data_type": dataset.data_type,
                    "data_location": dataset.data_location,
                    "authorized_at": str(gd.authorized_at) if gd.authorized_at else None,
                })

        return success(data=items)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


@router.get("/{group_id}/available-datasets")
def list_available_group_datasets(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取可授权数据集列表"""
    try:
        from app.models.group import GroupMember, GroupDataset
        from app.models.dataset import Dataset
        from app.services.access_control_service import (
            check_group_access,
            is_platform_admin,
            is_agency_admin,
        )

        check_group_access(db, current_user.id, group_id)

        if not is_platform_admin(db, current_user.id) and not is_agency_admin(db, current_user.id):
            return success(data=[])

        member_agency_ids = db.query(GroupMember.agency_id).filter(
            GroupMember.group_id == group_id,
            GroupMember.join_status == "active",
        ).all()
        member_agency_id_list = [r[0] for r in member_agency_ids if r[0]]

        if not member_agency_id_list:
            return success(data=[])

        authorized_dataset_ids = db.query(GroupDataset.dataset_id).filter(
            GroupDataset.group_id == group_id,
            GroupDataset.auth_status == "active",
        ).all()
        auth_ids = {r[0] for r in authorized_dataset_ids}

        query = db.query(Dataset).filter(
            Dataset.agency_id.in_(member_agency_id_list),
            ~Dataset.id.in_(auth_ids),
        )

        if is_agency_admin(db, current_user.id) and not is_platform_admin(db, current_user.id):
            user_agency_id = current_user.agency_id
            if user_agency_id:
                from app.models.agency import Agency
                visible_ids = [user_agency_id]
                def collect_descendants(parent_id: int):
                    children = db.query(Agency.id).filter(
                        Agency.parent_agency_id == parent_id,
                        Agency.status == "active",
                    ).all()
                    for child in children:
                        child_id = child[0]
                        if child_id not in visible_ids:
                            visible_ids.append(child_id)
                            collect_descendants(child_id)
                collect_descendants(user_agency_id)
                query = query.filter(Dataset.agency_id.in_(visible_ids))

        datasets = query.all()
        items = []
        for d in datasets:
            from app.models.agency import Agency
            agency = db.query(Agency).filter(Agency.id == d.agency_id).first()
            items.append({
                "id": d.id,
                "dataset_name": d.dataset_name,
                "dataset_code": d.dataset_code,
                "agency_id": d.agency_id,
                "agency_name": agency.agency_name if agency else None,
                "data_type": d.data_type,
            })

        return success(data=items)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


@router.post("/{group_id}/datasets")
def add_group_dataset(
    group_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """授权数据集到群组"""
    try:
        from app.models.group import GroupDataset
        from app.models.dataset import Dataset
        from app.services.access_control_service import (
            check_group_access,
            is_platform_admin,
            is_agency_admin,
        )
        from datetime import datetime

        check_group_access(db, current_user.id, group_id)

        if not is_platform_admin(db, current_user.id) and not is_agency_admin(db, current_user.id):
            raise HTTPException(status_code=403, detail="需要管理员权限")

        dataset_id = payload.get("dataset_id")
        if not dataset_id:
            raise HTTPException(status_code=400, detail="缺少dataset_id")

        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")

        existing = db.query(GroupDataset).filter(
            GroupDataset.group_id == group_id,
            GroupDataset.dataset_id == dataset_id,
        ).first()

        now = datetime.now()

        if existing:
            if existing.auth_status == "active":
                raise HTTPException(status_code=400, detail="该数据集已授权给当前群组")
            existing.auth_status = "active"
            existing.authorized_by = current_user.id
            existing.authorized_at = now
            existing.revoked_at = None
            existing.updated_at = now
        else:
            existing = GroupDataset(
                group_id=group_id,
                agency_id=dataset.agency_id,
                dataset_id=dataset_id,
                auth_status="active",
                authorized_by=current_user.id,
                authorized_at=now,
            )
            db.add(existing)

        db.commit()
        return success(data={"id": existing.id, "dataset_id": dataset_id})
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


@router.delete("/{group_id}/datasets/{dataset_id}")
def remove_group_dataset(
    group_id: int,
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """撤销数据集授权"""
    try:
        from app.models.group import GroupDataset
        from app.services.access_control_service import (
            check_group_access,
            is_platform_admin,
            is_agency_admin,
        )
        from datetime import datetime

        check_group_access(db, current_user.id, group_id)

        if not is_platform_admin(db, current_user.id) and not is_agency_admin(db, current_user.id):
            raise HTTPException(status_code=403, detail="需要管理员权限")

        gd = db.query(GroupDataset).filter(
            GroupDataset.group_id == group_id,
            GroupDataset.dataset_id == dataset_id,
        ).first()

        if not gd:
            raise HTTPException(status_code=404, detail="授权记录不存在")

        now = datetime.now()
        gd.auth_status = "revoked"
        gd.revoked_at = now
        gd.updated_at = now

        db.commit()
        return success(data={"id": gd.id})
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


# ============================================================
# 群组任务模板授权
# ============================================================

@router.get("/{group_id}/templates")
def list_group_templates(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取群组已授权任务模板列表"""
    try:
        from app.models.group import GroupTaskTemplate
        from app.models.stat_template import StatTemplate
        from app.services.access_control_service import check_group_access

        check_group_access(db, current_user.id, group_id)

        group_templates = db.query(GroupTaskTemplate).filter(
            GroupTaskTemplate.group_id == group_id,
            GroupTaskTemplate.auth_status == "active",
        ).all()

        items = []
        for gt in group_templates:
            template = db.query(StatTemplate).filter(StatTemplate.id == gt.template_id).first()
            if template:
                from app.models.agency import Agency
                agency = db.query(Agency).filter(Agency.id == template.agency_id).first() if template.agency_id else None
                items.append({
                    "id": gt.id,
                    "template_id": template.id,
                    "template_name": template.template_name,
                    "template_code": template.template_code,
                    "agency_id": template.agency_id,
                    "agency_name": agency.agency_name if agency else None,
                    "scenario": template.scenario,
                    "exec_mode": template.exec_mode,
                    "output_type": template.output_type,
                    "authorized_at": str(gt.authorized_at) if gt.authorized_at else None,
                })

        return success(data=items)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


@router.get("/{group_id}/available-templates")
def list_available_group_templates(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """获取可授权任务模板列表"""
    try:
        from app.models.group import GroupMember, GroupTaskTemplate
        from app.models.stat_template import StatTemplate
        from app.services.access_control_service import (
            check_group_access,
            is_platform_admin,
            is_agency_admin,
        )

        check_group_access(db, current_user.id, group_id)

        if not is_platform_admin(db, current_user.id) and not is_agency_admin(db, current_user.id):
            return success(data=[])

        member_agency_ids = db.query(GroupMember.agency_id).filter(
            GroupMember.group_id == group_id,
            GroupMember.join_status == "active",
        ).all()
        member_agency_id_list = [r[0] for r in member_agency_ids if r[0]]

        authorized_template_ids = db.query(GroupTaskTemplate.template_id).filter(
            GroupTaskTemplate.group_id == group_id,
            GroupTaskTemplate.auth_status == "active",
        ).all()
        auth_ids = {r[0] for r in authorized_template_ids}

        query = db.query(StatTemplate).filter(~StatTemplate.id.in_(auth_ids))

        if member_agency_id_list:
            query = query.filter(
                (StatTemplate.agency_id.in_(member_agency_id_list)) | (StatTemplate.agency_id.is_(None))
            )

        if is_agency_admin(db, current_user.id) and not is_platform_admin(db, current_user.id):
            user_agency_id = current_user.agency_id
            if user_agency_id:
                from app.models.agency import Agency
                visible_ids = [user_agency_id]
                def collect_descendants(parent_id: int):
                    children = db.query(Agency.id).filter(
                        Agency.parent_agency_id == parent_id,
                        Agency.status == "active",
                    ).all()
                    for child in children:
                        child_id = child[0]
                        if child_id not in visible_ids:
                            visible_ids.append(child_id)
                            collect_descendants(child_id)
                collect_descendants(user_agency_id)
                query = query.filter(
                    (StatTemplate.agency_id.in_(visible_ids)) | (StatTemplate.agency_id.is_(None))
                )

        templates = query.all()
        items = []
        for t in templates:
            from app.models.agency import Agency
            agency = db.query(Agency).filter(Agency.id == t.agency_id).first() if t.agency_id else None
            items.append({
                "id": t.id,
                "template_name": t.template_name,
                "template_code": t.template_code,
                "agency_id": t.agency_id,
                "agency_name": agency.agency_name if agency else None,
                "scenario": t.scenario,
            })

        return success(data=items)
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


@router.post("/{group_id}/templates")
def add_group_template(
    group_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """授权任务模板到群组"""
    try:
        from app.models.group import GroupTaskTemplate
        from app.models.stat_template import StatTemplate
        from app.services.access_control_service import (
            check_group_access,
            is_platform_admin,
            is_agency_admin,
        )
        from datetime import datetime

        check_group_access(db, current_user.id, group_id)

        if not is_platform_admin(db, current_user.id) and not is_agency_admin(db, current_user.id):
            raise HTTPException(status_code=403, detail="需要管理员权限")

        template_id = payload.get("template_id")
        if not template_id:
            raise HTTPException(status_code=400, detail="缺少template_id")

        template = db.query(StatTemplate).filter(StatTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        existing = db.query(GroupTaskTemplate).filter(
            GroupTaskTemplate.group_id == group_id,
            GroupTaskTemplate.template_id == template_id,
        ).first()

        now = datetime.now()

        if existing:
            if existing.auth_status == "active":
                raise HTTPException(status_code=400, detail="该模板已授权给当前群组")
            existing.auth_status = "active"
            existing.authorized_by = current_user.id
            existing.authorized_at = now
            existing.revoked_at = None
            existing.updated_at = now
        else:
            existing = GroupTaskTemplate(
                group_id=group_id,
                agency_id=template.agency_id,
                template_id=template_id,
                auth_status="active",
                authorized_by=current_user.id,
                authorized_at=now,
            )
            db.add(existing)

        db.commit()
        return success(data={"id": existing.id, "template_id": template_id})
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)


@router.delete("/{group_id}/templates/{template_id}")
def remove_group_template(
    group_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """撤销任务模板授权"""
    try:
        from app.models.group import GroupTaskTemplate
        from app.services.access_control_service import (
            check_group_access,
            is_platform_admin,
            is_agency_admin,
        )
        from datetime import datetime

        check_group_access(db, current_user.id, group_id)

        if not is_platform_admin(db, current_user.id) and not is_agency_admin(db, current_user.id):
            raise HTTPException(status_code=403, detail="需要管理员权限")

        gt = db.query(GroupTaskTemplate).filter(
            GroupTaskTemplate.group_id == group_id,
            GroupTaskTemplate.template_id == template_id,
        ).first()

        if not gt:
            raise HTTPException(status_code=404, detail="授权记录不存在")

        now = datetime.now()
        gt.auth_status = "revoked"
        gt.revoked_at = now
        gt.updated_at = now

        db.commit()
        return success(data={"id": gt.id})
    except Exception as e:
        if hasattr(e, "status_code"):
            raise
        return fail(message=str(e), code=500)
