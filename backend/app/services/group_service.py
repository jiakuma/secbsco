"""
群组管理服务：群组 CRUD、成员/用户/节点查询与授权、审批、创建群组事务。

核心方法：
- list_groups: 群组列表（权限过滤 + 分页）
- get_group_detail: 群组详情 + 统计摘要
- create_group_with_creator_admin: 创建群组事务（含权限判断和审批逻辑）
- update_group_basic_info: 编辑群组基础信息
- approve_group / reject_group: 群组审批
- list_group_members / add_group_member / remove_group_member: 成员机构管理
- list_group_users / add_group_user / update_group_user_role / remove_group_user: 用户授权管理
- list_group_nodes / list_available_group_nodes / add_group_node / remove_group_node: 节点授权管理
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, and_

from app.models.group import GroupInfo, GroupMember, GroupNode, GroupLifecycleLog
from app.models.user import SysUserGroup, SysUserRoleBinding, SysUserOperateLog
from app.models.sys_user import SysUser
from app.models.agency import Agency
from app.models.node import Node
from app.models.task import Task
from app.models.task_result import TaskResult
from app.models.chain_record import ChainRecord


# ============================================================
# 辅助函数
# ============================================================

def _format_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _get_agency_name(db: Session, agency_id: int | None) -> str | None:
    if not agency_id:
        return None
    agency = db.query(Agency).filter(Agency.id == agency_id).first()
    return agency.agency_name if agency else None


def _get_user_real_name(db: Session, user_id: int | None) -> str | None:
    if not user_id:
        return None
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    return user.real_name or user.username if user else None


def _write_lifecycle_log(
    db: Session,
    group_id: int,
    event_type: str,
    operator_user_id: int,
    operator_name: str,
    before_status: str | None = None,
    after_status: str | None = None,
    reason: str | None = None,
    detail: dict | None = None,
):
    """写入群组生命周期日志。"""
    db.add(GroupLifecycleLog(
        group_id=group_id,
        event_type=event_type,
        before_status=before_status,
        after_status=after_status,
        operator_user_id=operator_user_id,
        operator_name=operator_name,
        reason=reason,
        detail_json=detail,
    ))


def _write_operate_log(
    db: Session,
    user_id: int,
    username: str,
    operation_type: str,
    group_id: int | None = None,
    agency_id: int | None = None,
    resource_type: str = "group",
    resource_id: int | None = None,
    request=None,
):
    """写入用户操作日志。"""
    from app.services.access_control_service import write_operate_log
    write_operate_log(
        db,
        user_id=user_id,
        username=username,
        operation_type=operation_type,
        resource_type=resource_type,
        resource_id=resource_id,
        group_id=group_id,
        agency_id=agency_id,
        request=request,
    )


# ============================================================
# 群组列表
# ============================================================

def list_groups(
    db: Session,
    current_user: SysUser,
    keyword: str | None = None,
    status: str | None = None,
    region_code: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """
    根据当前用户权限返回可见群组列表（分页）。
    """
    from app.services.access_control_service import (
        get_accessible_group_ids,
        is_platform_admin,
        has_role,
    )

    base_query = db.query(GroupInfo)

    # 权限过滤
    accessible_ids = get_accessible_group_ids(db, current_user.id)
    if accessible_ids is not None:
        agency_admin_groups = set()
        if has_role(db, current_user.id, "admin", "agency"):
            agency_member_ids = (
                db.query(GroupMember.group_id)
                .filter(GroupMember.agency_id == current_user.agency_id)
                .distinct()
                .all()
            )
            agency_lead_ids = (
                db.query(GroupInfo.id)
                .filter(GroupInfo.lead_agency_id == current_user.agency_id)
                .distinct()
                .all()
            )
            agency_admin_groups = {r[0] for r in agency_member_ids} | {r[0] for r in agency_lead_ids}

        all_visible = set(accessible_ids) | agency_admin_groups
        base_query = base_query.filter(GroupInfo.id.in_(all_visible))

    if keyword:
        base_query = base_query.filter(
            or_(
                GroupInfo.group_code.like(f"%{keyword}%"),
                GroupInfo.group_name.like(f"%{keyword}%"),
            )
        )

    if status:
        base_query = base_query.filter(GroupInfo.status == status)

    if region_code:
        base_query = base_query.filter(GroupInfo.region_code == region_code)

    total = base_query.count()
    groups = (
        base_query
        .order_by(desc(GroupInfo.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for g in groups:
        member_count = (
            db.query(func.count(GroupMember.id))
            .filter(GroupMember.group_id == g.id, GroupMember.join_status == "active")
            .scalar() or 0
        )
        user_count = (
            db.query(func.count(SysUserGroup.id))
            .filter(SysUserGroup.group_id == g.id, SysUserGroup.join_status == "active")
            .scalar() or 0
        )
        node_count = (
            db.query(func.count(GroupNode.id))
            .filter(GroupNode.group_id == g.id, GroupNode.auth_status == "active")
            .scalar() or 0
        )

        items.append({
            "id": g.id,
            "group_code": g.group_code,
            "group_name": g.group_name,
            "group_level": g.group_level,
            "region_code": g.region_code,
            "region_name": g.region_name,
            "lead_agency_id": g.lead_agency_id,
            "lead_agency_name": _get_agency_name(db, g.lead_agency_id),
            "status": g.status,
            "approval_status": g.approval_status,
            "approval_required": g.approval_required,
            "created_by": g.created_by,
            "created_by_name": _get_user_real_name(db, g.created_by),
            "created_at": _format_dt(g.created_at),
            "member_count": member_count,
            "user_count": user_count,
            "node_count": node_count,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ============================================================
# 群组详情
# ============================================================

def get_group_detail(
    db: Session,
    group_id: int,
    current_user: SysUser,
) -> dict:
    """获取群组详情 + 统计摘要。"""
    from app.services.access_control_service import check_group_access

    check_group_access(db, current_user.id, group_id)

    group = db.query(GroupInfo).filter(GroupInfo.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="资源不存在或无权访问")

    member_count = (
        db.query(func.count(GroupMember.id))
        .filter(GroupMember.group_id == group_id, GroupMember.join_status == "active")
        .scalar() or 0
    )
    user_count = (
        db.query(func.count(SysUserGroup.id))
        .filter(SysUserGroup.group_id == group_id, SysUserGroup.join_status == "active")
        .scalar() or 0
    )
    admin_count = (
        db.query(func.count(SysUserRoleBinding.id))
        .filter(
            SysUserRoleBinding.scope_type == "group",
            SysUserRoleBinding.scope_id == group_id,
            SysUserRoleBinding.role_code == "admin",
            SysUserRoleBinding.status == "active",
        )
        .scalar() or 0
    )
    governor_count = (
        db.query(func.count(SysUserRoleBinding.id))
        .filter(
            SysUserRoleBinding.scope_type == "group",
            SysUserRoleBinding.scope_id == group_id,
            SysUserRoleBinding.role_code == "governor",
            SysUserRoleBinding.status == "active",
        )
        .scalar() or 0
    )
    node_count = (
        db.query(func.count(GroupNode.id))
        .filter(GroupNode.group_id == group_id, GroupNode.auth_status == "active")
        .scalar() or 0
    )
    task_count = (
        db.query(func.count(Task.id))
        .filter(Task.group_id == group_id)
        .scalar() or 0
    )
    result_count = (
        db.query(func.count(TaskResult.id))
        .filter(TaskResult.group_id == group_id)
        .scalar() or 0
    )
    chain_record_count = (
        db.query(func.count(ChainRecord.id))
        .filter(ChainRecord.group_id == group_id)
        .scalar() or 0
    )

    return {
        "id": group.id,
        "group_code": group.group_code,
        "group_name": group.group_name,
        "group_level": group.group_level,
        "region_code": group.region_code,
        "region_name": group.region_name,
        "lead_agency_id": group.lead_agency_id,
        "lead_agency_name": _get_agency_name(db, group.lead_agency_id),
        "description": group.description,
        "status": group.status,
        "approval_status": group.approval_status,
        "approval_required": group.approval_required,
        "approval_agency_id": group.approval_agency_id,
        "creator_agency_id": group.creator_agency_id,
        "created_by": group.created_by,
        "created_by_name": _get_user_real_name(db, group.created_by),
        "created_at": _format_dt(group.created_at),
        "updated_at": _format_dt(group.updated_at),
        "summary": {
            "member_count": member_count,
            "user_count": user_count,
            "admin_count": admin_count,
            "governor_count": governor_count,
            "node_count": node_count,
            "task_count": task_count,
            "result_count": result_count,
            "chain_record_count": chain_record_count,
        },
    }


# ============================================================
# 创建群组（事务）- 第4阶段重写
# ============================================================

def create_group_with_creator_admin(
    db: Session,
    payload: dict,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """
    创建群组，权限判断规则：
    1. 平台管理员 -> 直接创建，status=draft，无需审批
    2. 机构管理员（上级创建下级） -> 直接创建，status=draft，无需审批
    3. 机构管理员（同级协作） -> pending_approval，需审批
    4. 群组管理员 -> 403 禁止
    5. 普通用户/治理员 -> 403 禁止
    """
    from app.services.access_control_service import (
        is_platform_admin,
        is_agency_admin,
        has_role,
        is_ancestor_agency,
        is_same_level_agency,
        find_common_parent_agency,
    )

    lead_agency_id = payload.get("lead_agency_id")
    member_agency_ids = payload.get("member_agency_ids", [])

    # ---------- 权限校验 ----------
    now = datetime.now()
    group_status = "draft"
    approval_required = False
    approval_status_str = "none"
    approval_agency_id_val = None

    if is_platform_admin(db, current_user.id):
        # 平台管理员：直接创建
        group_status = "draft"
        approval_required = False
        approval_status_str = "none"
    elif is_agency_admin(db, current_user.id):
        # 机构管理员：判断上下级关系
        user_agency_id = current_user.agency_id

        # 牵头机构必须是自己的机构
        if lead_agency_id != user_agency_id:
            raise HTTPException(status_code=403, detail="机构管理员只能以本机构作为牵头机构")

        # 收集所有相关机构ID（牵头 + 成员）
        all_agency_ids = [lead_agency_id] + [aid for aid in member_agency_ids if aid != lead_agency_id]

        # 判断是否所有目标机构都是本机构的下级
        all_are_descendants = True
        all_are_same_level = True

        for aid in all_agency_ids:
            if aid == user_agency_id:
                continue
            if not is_ancestor_agency(db, user_agency_id, aid):
                all_are_descendants = False
            if not is_same_level_agency(db, user_agency_id, aid):
                all_are_same_level = False

        if all_are_descendants:
            # 上级创建下级群组：直接创建
            group_status = "draft"
            approval_required = False
            approval_status_str = "none"
        else:
            # 同级协作或无法判断：需要审批
            group_status = "pending_approval"
            approval_required = True
            approval_status_str = "pending"
            # 查找共同上级
            common_parent = find_common_parent_agency(db, all_agency_ids)
            approval_agency_id_val = common_parent  # None 则由平台管理员审批
    elif has_role(db, current_user.id, "admin", "group"):
        # 群组管理员不能创建新群组
        raise HTTPException(
            status_code=403,
            detail="群组管理员不能创建新群组，请使用机构管理员账号发起创建",
        )
    else:
        raise HTTPException(status_code=403, detail="需要管理员权限才能创建群组")

    # ---------- 校验牵头机构存在 ----------
    agency = db.query(Agency).filter(Agency.id == lead_agency_id).first()
    if not agency:
        raise HTTPException(status_code=400, detail="牵头机构不存在")

    # ---------- group_code 唯一性 ----------
    group_code = payload.get("group_code")
    existing = db.query(GroupInfo).filter(GroupInfo.group_code == group_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="群组编码已存在")

    # ---------- 1. 创建 group_info ----------
    group = GroupInfo(
        group_code=group_code,
        group_name=payload.get("group_name"),
        group_level=payload.get("group_level", "city"),
        region_code=payload.get("region_code"),
        region_name=payload.get("region_name"),
        lead_agency_id=lead_agency_id,
        description=payload.get("description"),
        status=group_status,
        created_by=current_user.id,
        creator_agency_id=current_user.agency_id,
        approval_required=approval_required,
        approval_status=approval_status_str,
        approval_agency_id=approval_agency_id_val,
    )
    db.add(group)
    db.flush()

    # ---------- 2. 牵头机构自动写入 group_member ----------
    db.add(GroupMember(
        group_id=group.id,
        agency_id=lead_agency_id,
        member_role="lead_agency",
        is_lead=True,
        join_status="active",
        joined_at=now,
    ))

    # ---------- 3. 成员机构写入 group_member ----------
    for aid in member_agency_ids:
        if aid == lead_agency_id:
            continue
        member_agency = db.query(Agency).filter(Agency.id == aid).first()
        if not member_agency:
            continue
        # 检查重复
        existing_member = db.query(GroupMember).filter(
            GroupMember.group_id == group.id,
            GroupMember.agency_id == aid,
        ).first()
        if existing_member:
            continue
        db.add(GroupMember(
            group_id=group.id,
            agency_id=aid,
            member_role="participant",
            is_lead=False,
            join_status="active",
            joined_at=now,
        ))

    # ---------- 4. 创建人自动写入 sys_user_group ----------
    db.add(SysUserGroup(
        user_id=current_user.id,
        group_id=group.id,
        agency_id=current_user.agency_id,
        join_status="active",
        authorized_by=current_user.id,
        authorized_at=now,
    ))

    # ---------- 5. 创建人自动写入 sys_user_role_binding (admin + group) ----------
    db.add(SysUserRoleBinding(
        user_id=current_user.id,
        role_code="admin",
        scope_type="group",
        scope_id=group.id,
        status="active",
        created_by=current_user.id,
    ))

    # ---------- 6. group_lifecycle_log ----------
    log_reason = "创建群组（直接创建）" if not approval_required else "创建群组（同级协作，等待审批）"
    _write_lifecycle_log(
        db,
        group_id=group.id,
        event_type="group_created",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=None,
        after_status=group_status,
        reason=log_reason,
        detail={
            "group_code": group.group_code,
            "group_name": group.group_name,
            "lead_agency_id": group.lead_agency_id,
            "approval_required": approval_required,
            "approval_status": approval_status_str,
            "approval_agency_id": approval_agency_id_val,
        },
    )

    # ---------- 7. sys_user_operate_log ----------
    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="group_created",
        group_id=group.id,
        agency_id=current_user.agency_id,
        request=request,
    )

    db.commit()
    db.refresh(group)

    return {
        "id": group.id,
        "group_code": group.group_code,
        "group_name": group.group_name,
        "status": group.status,
        "approval_status": group.approval_status,
        "approval_required": group.approval_required,
        "approval_agency_id": group.approval_agency_id,
        "created_by": current_user.id,
        "created_admin_role_created": True,
        "lead_agency_member_created": True,
        "lifecycle_log_created": True,
    }


# ============================================================
# 编辑群组基础信息
# ============================================================

def update_group_basic_info(
    db: Session,
    group_id: int,
    payload: dict,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """更新群组基础信息。"""
    from app.services.access_control_service import check_group_admin_access

    check_group_admin_access(db, current_user.id, group_id)

    group = db.query(GroupInfo).filter(GroupInfo.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    if group.status in ("archived", "rejected", "dissolved"):
        raise HTTPException(status_code=400, detail="当前状态的群组不允许编辑")

    update_fields = ["group_name", "group_level", "region_code", "region_name", "description"]
    changed = False
    for field in update_fields:
        if field in payload and payload[field] is not None:
            setattr(group, field, payload[field])
            changed = True

    if not changed:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    group.updated_at = datetime.now()

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="group_updated",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=group.status,
        after_status=group.status,
        reason="更新群组基础信息",
        detail=payload,
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="group_updated",
        resource_id=group_id,
        group_id=group_id,
        agency_id=current_user.agency_id,
        request=request,
    )

    db.commit()
    db.refresh(group)

    return {
        "id": group.id,
        "group_code": group.group_code,
        "group_name": group.group_name,
        "status": group.status,
    }


# ============================================================
# 群组审批
# ============================================================

def approve_group(
    db: Session,
    group_id: int,
    payload: dict,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """审批通过群组。"""
    from app.services.access_control_service import can_approve_group

    group = db.query(GroupInfo).filter(GroupInfo.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    if group.status != "pending_approval":
        raise HTTPException(status_code=400, detail="群组不在待审批状态")
    if group.approval_status != "pending":
        raise HTTPException(status_code=400, detail="群组审批状态不是待审批")

    if not can_approve_group(db, current_user.id, group):
        raise HTTPException(status_code=403, detail="您没有审批该群组的权限")

    now = datetime.now()
    old_status = group.status
    group.status = "draft"
    group.approval_status = "approved"
    group.approved_by = current_user.id
    group.approved_at = now
    group.updated_at = now

    remark = payload.get("remark", "审批通过")

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="group_approved",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=old_status,
        after_status="draft",
        reason=remark,
        detail={"approved_by": current_user.id, "remark": remark},
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="group_approved",
        resource_id=group_id,
        group_id=group_id,
        request=request,
    )

    db.commit()
    db.refresh(group)

    return {"id": group.id, "status": group.status, "approval_status": group.approval_status}


def reject_group(
    db: Session,
    group_id: int,
    payload: dict,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """驳回群组申请。"""
    from app.services.access_control_service import can_approve_group

    group = db.query(GroupInfo).filter(GroupInfo.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    if group.status != "pending_approval":
        raise HTTPException(status_code=400, detail="群组不在待审批状态")
    if group.approval_status != "pending":
        raise HTTPException(status_code=400, detail="群组审批状态不是待审批")

    if not can_approve_group(db, current_user.id, group):
        raise HTTPException(status_code=403, detail="您没有驳回该群组的权限")

    now = datetime.now()
    reason = payload.get("reason", "")
    old_status = group.status
    group.status = "rejected"
    group.approval_status = "rejected"
    group.rejected_by = current_user.id
    group.rejected_at = now
    group.reject_reason = reason
    group.updated_at = now

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="group_rejected",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=old_status,
        after_status="rejected",
        reason=f"驳回：{reason}",
        detail={"rejected_by": current_user.id, "reason": reason},
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="group_rejected",
        resource_id=group_id,
        group_id=group_id,
        request=request,
    )

    db.commit()
    db.refresh(group)

    return {"id": group.id, "status": group.status, "approval_status": group.approval_status}


# ============================================================
# 群组成员机构管理
# ============================================================

def list_group_members(
    db: Session,
    group_id: int,
    current_user: SysUser,
) -> list[dict]:
    """查询群组当前有效成员机构。

    说明：
    group_member 使用软删除保留历史记录，移除成员时会把 join_status 改为 removed。
    当前页面只应该展示 active 成员，removed/disabled/archived 记录只保留给日志和审计使用。
    """
    from app.services.access_control_service import check_group_access

    check_group_access(db, current_user.id, group_id)

    members = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.join_status == "active",
        )
        .order_by(GroupMember.is_lead.desc(), GroupMember.id.asc())
        .all()
    )

    items = []
    for m in members:
        agency_name = _get_agency_name(db, m.agency_id)
        items.append({
            "id": m.id,
            "group_id": m.group_id,
            "agency_id": m.agency_id,
            "agency_name": agency_name,
            "member_role": m.member_role,
            "is_lead": m.is_lead,
            "join_status": m.join_status,
            "joined_at": _format_dt(m.joined_at),
        })

    return items


def add_group_member(
    db: Session,
    group_id: int,
    payload: dict,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """添加成员机构到群组。"""
    from app.services.access_control_service import check_group_admin_access

    check_group_admin_access(db, current_user.id, group_id)

    group = db.query(GroupInfo).filter(GroupInfo.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    agency_id = payload.get("agency_id")
    member_type = payload.get("member_type", "participant")
    remark = payload.get("remark", "")

    # 校验机构存在
    agency = db.query(Agency).filter(Agency.id == agency_id).first()
    if not agency:
        raise HTTPException(status_code=400, detail="机构不存在")
    if agency.status != "active":
        raise HTTPException(status_code=400, detail="该机构未启用，不能加入群组")

    # group_member 表存在 group_id + agency_id 唯一约束。
    # 因此不能在历史 removed 记录存在时直接新增，否则会触发唯一键冲突。
    # 正确逻辑：active 记录判定为重复；removed/disabled/archived/pending 记录重新激活。
    existing = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.agency_id == agency_id,
    ).first()

    if existing and existing.join_status == "active":
        raise HTTPException(status_code=400, detail="该机构已是群组成员，不能重复添加")

    now = datetime.now()
    reactivated = False

    if existing:
        existing.member_role = member_type
        existing.is_lead = False
        existing.join_status = "active"
        existing.joined_at = now
        existing.removed_at = None
        if hasattr(existing, "disabled_at"):
            existing.disabled_at = None
        existing.updated_at = now
        reactivated = True
    else:
        db.add(GroupMember(
            group_id=group_id,
            agency_id=agency_id,
            member_role=member_type,
            is_lead=False,
            join_status="active",
            joined_at=now,
        ))

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="member_added",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=group.status,
        after_status=group.status,
        reason=f"添加成员机构：{agency.agency_name}（{remark}）",
        detail={
            "agency_id": agency_id,
            "agency_name": agency.agency_name,
            "member_type": member_type,
            "reactivated": reactivated,
        },
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="member_added",
        resource_id=group_id,
        group_id=group_id,
        agency_id=agency_id,
        request=request,
    )

    db.commit()

    return {
        "group_id": group_id,
        "agency_id": agency_id,
        "agency_name": agency.agency_name,
        "reactivated": reactivated,
    }


def remove_group_member(
    db: Session,
    group_id: int,
    agency_id: int,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """移除群组成员机构。"""
    from app.services.access_control_service import check_group_admin_access

    check_group_admin_access(db, current_user.id, group_id)

    group = db.query(GroupInfo).filter(GroupInfo.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.agency_id == agency_id,
        GroupMember.join_status == "active",
    ).first()
    if not member:
        raise HTTPException(status_code=400, detail="该机构不是当前群组的活跃成员")

    # 不能移除牵头机构
    if member.is_lead:
        raise HTTPException(status_code=400, detail="不能移除牵头机构")

    # 检查该机构下是否有用户或节点授权
    has_users = (
        db.query(SysUserGroup.id)
        .filter(
            SysUserGroup.group_id == group_id,
            SysUserGroup.agency_id == agency_id,
            SysUserGroup.join_status == "active",
        )
        .first()
    )
    if has_users:
        agency_name = _get_agency_name(db, agency_id)
        raise HTTPException(
            status_code=400,
            detail=f"机构「{agency_name}」下已有用户加入该群组，请先移除相关用户再移除机构",
        )

    has_nodes = (
        db.query(GroupNode.id)
        .filter(
            GroupNode.group_id == group_id,
            GroupNode.agency_id == agency_id,
            GroupNode.auth_status == "active",
        )
        .first()
    )
    if has_nodes:
        agency_name = _get_agency_name(db, agency_id)
        raise HTTPException(
            status_code=400,
            detail=f"机构「{agency_name}」下已有节点授权到该群组，请先取消节点授权再移除机构",
        )

    now = datetime.now()
    member.join_status = "removed"
    member.removed_at = now

    agency_name = _get_agency_name(db, agency_id)

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="member_removed",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=group.status,
        after_status=group.status,
        reason=f"移除成员机构：{agency_name}",
        detail={"agency_id": agency_id, "agency_name": agency_name},
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="member_removed",
        resource_id=group_id,
        group_id=group_id,
        agency_id=agency_id,
        request=request,
    )

    db.commit()

    return {"group_id": group_id, "agency_id": agency_id, "removed": True}


# ============================================================
# 群组用户授权管理
# ============================================================

def list_group_users(
    db: Session,
    group_id: int,
    current_user: SysUser,
) -> list[dict]:
    """查询群组用户及其群组角色。"""
    from app.services.access_control_service import check_group_access

    check_group_access(db, current_user.id, group_id)

    user_groups = (
        db.query(SysUserGroup)
        .filter(
            SysUserGroup.group_id == group_id,
            SysUserGroup.join_status == "active",
        )
        .all()
    )

    items = []
    for ug in user_groups:
        user = db.query(SysUser).filter(SysUser.id == ug.user_id).first()
        if not user:
            continue

        agency_name = _get_agency_name(db, user.agency_id)

        role_bindings = (
            db.query(SysUserRoleBinding)
            .filter(
                SysUserRoleBinding.user_id == ug.user_id,
                SysUserRoleBinding.scope_type == "group",
                SysUserRoleBinding.scope_id == group_id,
                SysUserRoleBinding.status == "active",
            )
            .all()
        )

        roles = [{"role_code": rb.role_code, "scope_type": rb.scope_type, "scope_id": rb.scope_id} for rb in role_bindings]

        items.append({
            "user_id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "agency_id": user.agency_id,
            "agency_name": agency_name,
            "join_status": ug.join_status,
            "roles": roles,
        })

    return items


def add_group_user(
    db: Session,
    group_id: int,
    payload: dict,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """将用户加入群组并授权角色。"""
    from app.services.access_control_service import check_group_admin_access, is_agency_admin

    check_group_admin_access(db, current_user.id, group_id)

    group = db.query(GroupInfo).filter(GroupInfo.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    user_id = payload.get("user_id")
    role_code = payload.get("role_code", "user")

    # 校验用户存在
    target_user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=400, detail="用户不存在")
    if target_user.status != "active":
        raise HTTPException(status_code=400, detail="该用户未启用")

    # 用户所属机构必须是群组成员机构
    is_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.agency_id == target_user.agency_id,
        GroupMember.join_status == "active",
    ).first()
    if not is_member:
        raise HTTPException(status_code=400, detail="该用户所属机构不是当前群组的成员机构")

    # role_code 只允许 admin、user、governor
    if role_code not in ("admin", "user", "governor"):
        raise HTTPException(status_code=400, detail="群组角色只允许 admin、user、governor")

    # 如果 role_code = admin，必须验证该用户本身是其所属机构的机构管理员
    if role_code == "admin":
        if not is_agency_admin(db, user_id, target_user.agency_id):
            raise HTTPException(
                status_code=400,
                detail="只有机构管理员才能被授权为群组管理员",
            )

    now = datetime.now()

    # 写入或更新 sys_user_group（幂等）
    existing_ug = db.query(SysUserGroup).filter(
        SysUserGroup.user_id == user_id,
        SysUserGroup.group_id == group_id,
    ).first()
    if existing_ug:
        if existing_ug.join_status == "active":
            raise HTTPException(status_code=400, detail="该用户已在群组中")
        # 重新激活
        existing_ug.join_status = "active"
        existing_ug.authorized_by = current_user.id
        existing_ug.authorized_at = now
    else:
        db.add(SysUserGroup(
            user_id=user_id,
            group_id=group_id,
            agency_id=target_user.agency_id,
            join_status="active",
            authorized_by=current_user.id,
            authorized_at=now,
        ))

    # 写入或更新 sys_user_role_binding
    existing_rb = db.query(SysUserRoleBinding).filter(
        SysUserRoleBinding.user_id == user_id,
        SysUserRoleBinding.scope_type == "group",
        SysUserRoleBinding.scope_id == group_id,
        SysUserRoleBinding.role_code == role_code,
    ).first()
    if existing_rb:
        if existing_rb.status == "active":
            raise HTTPException(status_code=400, detail="该用户已拥有此群组角色")
        existing_rb.status = "active"
    else:
        db.add(SysUserRoleBinding(
            user_id=user_id,
            role_code=role_code,
            scope_type="group",
            scope_id=group_id,
            status="active",
            created_by=current_user.id,
        ))

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="user_added",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=group.status,
        after_status=group.status,
        reason=f"用户「{target_user.real_name or target_user.username}」加入群组，角色：{role_code}",
        detail={"user_id": user_id, "username": target_user.username, "role_code": role_code},
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="user_added",
        resource_id=group_id,
        group_id=group_id,
        agency_id=current_user.agency_id,
        request=request,
    )

    db.commit()

    return {
        "user_id": user_id,
        "username": target_user.username,
        "role_code": role_code,
        "group_id": group_id,
    }


def update_group_user_role(
    db: Session,
    group_id: int,
    user_id: int,
    payload: dict,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """修改用户在当前群组内的角色。"""
    from app.services.access_control_service import check_group_admin_access, is_agency_admin

    check_group_admin_access(db, current_user.id, group_id)

    new_role_code = payload.get("role_code")
    if new_role_code not in ("admin", "user", "governor"):
        raise HTTPException(status_code=400, detail="群组角色只允许 admin、user、governor")

    # 用户必须已加入群组
    ug = db.query(SysUserGroup).filter(
        SysUserGroup.user_id == user_id,
        SysUserGroup.group_id == group_id,
        SysUserGroup.join_status == "active",
    ).first()
    if not ug:
        raise HTTPException(status_code=400, detail="该用户未加入当前群组")

    target_user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=400, detail="用户不存在")

    # 查询当前角色
    current_rb = db.query(SysUserRoleBinding).filter(
        SysUserRoleBinding.user_id == user_id,
        SysUserRoleBinding.scope_type == "group",
        SysUserRoleBinding.scope_id == group_id,
        SysUserRoleBinding.status == "active",
    ).first()

    if current_rb and current_rb.role_code == new_role_code:
        raise HTTPException(status_code=400, detail="用户已拥有该角色，无需修改")

    # 如果修改为 admin，需要校验用户是否为其所属机构的机构管理员
    if new_role_code == "admin":
        if not is_agency_admin(db, user_id, target_user.agency_id):
            raise HTTPException(
                status_code=400,
                detail="只有机构管理员才能被授权为群组管理员",
            )

    # 如果把 admin 改为 user 或 governor，检查不能导致群组没有 admin
    if current_rb and current_rb.role_code == "admin" and new_role_code != "admin":
        admin_count = (
            db.query(func.count(SysUserRoleBinding.id))
            .filter(
                SysUserRoleBinding.scope_type == "group",
                SysUserRoleBinding.scope_id == group_id,
                SysUserRoleBinding.role_code == "admin",
                SysUserRoleBinding.status == "active",
            )
            .scalar() or 0
        )
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="不能取消当前群组最后一个管理员的角色，请先授权其他管理员",
            )

    old_role = current_rb.role_code if current_rb else None

    # 更新或创建角色绑定
    if current_rb:
        current_rb.role_code = new_role_code
    else:
        db.add(SysUserRoleBinding(
            user_id=user_id,
            role_code=new_role_code,
            scope_type="group",
            scope_id=group_id,
            status="active",
            created_by=current_user.id,
        ))

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="user_role_updated",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=group.status,
        after_status=group.status,
        reason=f"修改用户「{target_user.real_name or target_user.username}」群组角色：{old_role} -> {new_role_code}",
        detail={"user_id": user_id, "old_role": old_role, "new_role": new_role_code},
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="user_role_updated",
        resource_id=group_id,
        group_id=group_id,
        request=request,
    )

    db.commit()

    return {"user_id": user_id, "old_role": old_role, "new_role": new_role_code}


def remove_group_user(
    db: Session,
    group_id: int,
    user_id: int,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """将用户移出群组。"""
    from app.services.access_control_service import check_group_admin_access

    check_group_admin_access(db, current_user.id, group_id)

    # 用户必须已加入群组
    ug = db.query(SysUserGroup).filter(
        SysUserGroup.user_id == user_id,
        SysUserGroup.group_id == group_id,
        SysUserGroup.join_status == "active",
    ).first()
    if not ug:
        raise HTTPException(status_code=400, detail="该用户未加入当前群组")

    target_user = db.query(SysUser).filter(SysUser.id == user_id).first()

    # 检查是否是最后一个管理员
    is_admin_user = db.query(SysUserRoleBinding).filter(
        SysUserRoleBinding.user_id == user_id,
        SysUserRoleBinding.scope_type == "group",
        SysUserRoleBinding.scope_id == group_id,
        SysUserRoleBinding.role_code == "admin",
        SysUserRoleBinding.status == "active",
    ).first()

    if is_admin_user:
        admin_count = (
            db.query(func.count(SysUserRoleBinding.id))
            .filter(
                SysUserRoleBinding.scope_type == "group",
                SysUserRoleBinding.scope_id == group_id,
                SysUserRoleBinding.role_code == "admin",
                SysUserRoleBinding.status == "active",
            )
            .scalar() or 0
        )
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="不能移出当前群组最后一个管理员，请先授权其他管理员",
            )

    now = datetime.now()
    ug.join_status = "disabled"
    ug.disabled_at = now

    # 将该用户在群组下的角色绑定置为 disabled
    db.query(SysUserRoleBinding).filter(
        SysUserRoleBinding.user_id == user_id,
        SysUserRoleBinding.scope_type == "group",
        SysUserRoleBinding.scope_id == group_id,
        SysUserRoleBinding.status == "active",
    ).update({"status": "disabled", "disabled_at": now})

    username = target_user.real_name or target_user.username if target_user else str(user_id)

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="user_removed",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=None,
        after_status=None,
        reason=f"用户「{username}」移出群组",
        detail={"user_id": user_id, "username": username},
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="user_removed",
        resource_id=group_id,
        group_id=group_id,
        request=request,
    )

    db.commit()

    return {"user_id": user_id, "removed": True}


# ============================================================
# 群组节点授权管理
# ============================================================

def list_group_nodes(
    db: Session,
    group_id: int,
    current_user: SysUser,
    node_type: str | None = None,
    node_usage_role: str | None = None,
    auth_status: str | None = None,
) -> list[dict]:
    """查询群组已授权节点。"""
    from app.services.access_control_service import check_group_access

    check_group_access(db, current_user.id, group_id)

    query = db.query(GroupNode).filter(GroupNode.group_id == group_id)

    if node_type:
        query = query.join(Node, GroupNode.node_id == Node.id).filter(Node.node_type == node_type)
    if node_usage_role:
        query = query.filter(GroupNode.node_usage_role == node_usage_role)
    if auth_status:
        query = query.filter(GroupNode.auth_status == auth_status)

    group_nodes = query.all()

    items = []
    for gn in group_nodes:
        node = db.query(Node).filter(Node.id == gn.node_id).first()
        if not node:
            continue

        items.append({
            "group_node_id": gn.id,
            "node_id": node.id,
            "node_code": node.node_code,
            "node_name": node.node_name,
            "agency_id": node.agency_id,
            "agency_name": _get_agency_name(db, node.agency_id),
            "node_type": node.node_type,
            "node_usage_role": gn.node_usage_role,
            "auth_status": gn.auth_status,
            "node_status": node.status,
            "node_load_status": node.node_load_status,
        })

    return items


def list_available_group_nodes(
    db: Session,
    group_id: int,
    current_user: SysUser,
) -> list[dict]:
    """返回当前群组可授权节点列表（来自成员机构）。"""
    from app.services.access_control_service import check_group_access

    check_group_access(db, current_user.id, group_id)

    # 获取群组成员机构ID
    member_agency_ids = (
        db.query(GroupMember.agency_id)
        .filter(GroupMember.group_id == group_id, GroupMember.join_status == "active")
        .all()
    )
    agency_ids = [r[0] for r in member_agency_ids]
    if not agency_ids:
        return []

    # 获取已授权节点ID
    authorized_node_ids = (
        db.query(GroupNode.node_id)
        .filter(
            GroupNode.group_id == group_id,
            GroupNode.auth_status == "active",
        )
        .all()
    )
    auth_ids = {r[0] for r in authorized_node_ids}

    # 查询成员机构的活跃节点
    nodes = (
        db.query(Node)
        .filter(
            Node.agency_id.in_(agency_ids),
            Node.status == "active",
        )
        .all()
    )

    items = []
    for node in nodes:
        items.append({
            "node_id": node.id,
            "node_code": node.node_code,
            "node_name": node.node_name,
            "agency_id": node.agency_id,
            "agency_name": _get_agency_name(db, node.agency_id),
            "node_type": node.node_type,
            "node_status": node.status,
            "authorized": node.id in auth_ids,
        })

    return items


def add_group_node(
    db: Session,
    group_id: int,
    payload: dict,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """授权节点给群组。"""
    from app.services.access_control_service import check_group_admin_access

    check_group_admin_access(db, current_user.id, group_id)

    group = db.query(GroupInfo).filter(GroupInfo.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    node_id = payload.get("node_id")
    remark = payload.get("remark", "")

    # 校验节点存在
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=400, detail="节点不存在")
    if node.status != "active":
        raise HTTPException(status_code=400, detail="该节点未启用，不能授权")

    # 节点所属机构必须是群组成员
    is_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.agency_id == node.agency_id,
        GroupMember.join_status == "active",
    ).first()
    if not is_member:
        raise HTTPException(status_code=400, detail="非成员机构节点不能授权给当前群组")

    # 不能重复授权
    existing = db.query(GroupNode).filter(
        GroupNode.group_id == group_id,
        GroupNode.node_id == node_id,
        GroupNode.auth_status == "active",
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该节点已授权给当前群组，不能重复授权")

    now = datetime.now()

    # 推断 node_usage_role
    node_usage_role = "group_data"
    if node.node_type in ("compute_node",):
        node_usage_role = "group_compute"
    elif node.node_type in ("blockchain_node",):
        node_usage_role = "group_blockchain"
    elif node.node_type in ("service_node", "gateway_node"):
        node_usage_role = "group_service"

    db.add(GroupNode(
        group_id=group_id,
        agency_id=node.agency_id,
        node_id=node_id,
        node_usage_role=node_usage_role,
        auth_status="active",
        authorized_by=current_user.id,
        authorized_at=now,
    ))

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="node_authorized",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=group.status,
        after_status=group.status,
        reason=f"授权节点「{node.node_name}」给群组（{remark}）",
        detail={"node_id": node_id, "node_code": node.node_code, "node_name": node.node_name, "agency_id": node.agency_id},
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="node_authorized",
        resource_id=group_id,
        group_id=group_id,
        agency_id=node.agency_id,
        request=request,
    )

    db.commit()

    return {"node_id": node_id, "node_name": node.node_name, "authorized": True}


def remove_group_node(
    db: Session,
    group_id: int,
    node_id: int,
    current_user: SysUser,
    request: "Request" = None,
) -> dict:
    """取消群组节点授权。"""
    from app.services.access_control_service import check_group_admin_access

    check_group_admin_access(db, current_user.id, group_id)

    gn = db.query(GroupNode).filter(
        GroupNode.group_id == group_id,
        GroupNode.node_id == node_id,
        GroupNode.auth_status == "active",
    ).first()
    if not gn:
        raise HTTPException(status_code=400, detail="该节点未授权给当前群组")

    # 检查是否有任务使用该节点（本阶段简化检查）
    has_tasks = (
        db.query(Task.id)
        .filter(Task.group_id == group_id)
        .first()
    )
    if has_tasks:
        node = db.query(Node).filter(Node.id == node_id).first()
        node_name = node.node_name if node else str(node_id)
        raise HTTPException(
            status_code=400,
            detail=f"群组已有任务关联，暂不能取消节点「{node_name}」的授权",
        )

    now = datetime.now()
    gn.auth_status = "revoked"
    gn.revoked_at = now

    node = db.query(Node).filter(Node.id == node_id).first()

    _write_lifecycle_log(
        db,
        group_id=group_id,
        event_type="node_revoked",
        operator_user_id=current_user.id,
        operator_name=current_user.real_name or current_user.username,
        before_status=None,
        after_status=None,
        reason=f"取消节点「{node.node_name if node else node_id}」授权",
        detail={"node_id": node_id, "node_name": node.node_name if node else None},
    )

    _write_operate_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="node_revoked",
        resource_id=group_id,
        group_id=group_id,
        request=request,
    )

    db.commit()

    return {"node_id": node_id, "revoked": True}
