from datetime import datetime
from sqlalchemy.orm import Session
from app.models.group import GroupInfo as GroupORM, GroupMember as GroupMemberORM, GroupNode as GroupNodeORM, GroupDataset as GroupDatasetORM, GroupTaskTemplate as GroupTemplateORM, GroupLifecycleLog
from app.models.sys_user import SysUser
from app.models.user import SysUserGroup, SysUserRoleBinding
from app.models.agency import Agency
from app.models.node import Node as NodeORM
from app.models.dataset import Dataset as DatasetORM
from app.models.stat_template import StatTemplate as TemplateORM
from ..domain.models import GroupInfo, GroupMember, GroupNodeAuth, GroupDatasetAuth, GroupTemplateAuth
from ..domain.ports import (
    GroupRepository, GroupMemberRepository, GroupNodeRepository,
    GroupDatasetRepository, GroupTemplateRepository,
    AccessControlPort, AuditLogPort, UserQueryPort, AgencyQueryPort, LifecycleLogRepository,
)


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _group_to_domain(orm: GroupORM) -> GroupInfo:
    return GroupInfo(
        id=orm.id, group_code=orm.group_code, group_name=orm.group_name,
        group_level=orm.group_level, region_code=orm.region_code, region_name=orm.region_name,
        lead_agency_id=orm.lead_agency_id, description=orm.description, status=orm.status,
        created_by=orm.created_by, creator_agency_id=orm.creator_agency_id,
        created_at=orm.created_at, updated_at=orm.updated_at,
        approval_required=orm.approval_required, approval_status=orm.approval_status,
        approval_agency_id=orm.approval_agency_id, approved_by=orm.approved_by, approved_at=orm.approved_at,
        rejected_by=orm.rejected_by, rejected_at=orm.rejected_at, reject_reason=orm.reject_reason,
        activated_at=orm.activated_at, dissolved_at=orm.dissolved_at, dissolve_reason=orm.dissolve_reason,
        delete_approval_status=orm.delete_approval_status, delete_approval_agency_id=orm.delete_approval_agency_id,
        delete_requested_by=orm.delete_requested_by, delete_requested_at=orm.delete_requested_at,
        delete_approved_by=orm.delete_approved_by, delete_approved_at=orm.delete_approved_at,
        delete_rejected_by=orm.delete_rejected_by, delete_rejected_at=orm.delete_rejected_at,
        delete_reject_reason=orm.delete_reject_reason,
    )


def _member_to_domain(orm: GroupMemberORM) -> GroupMember:
    return GroupMember(
        id=orm.id, group_id=orm.group_id, agency_id=orm.agency_id,
        member_role=orm.member_role, is_lead=orm.is_lead,
        join_status=orm.join_status, joined_at=orm.joined_at, removed_at=orm.removed_at,
        created_at=orm.created_at, updated_at=orm.updated_at,
    )


class SQLAlchemyGroupRepository(GroupRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, group_id: int) -> GroupInfo | None:
        orm = self._db.query(GroupORM).filter(GroupORM.id == group_id).first()
        return _group_to_domain(orm) if orm else None

    def get_by_code(self, group_code: str) -> GroupInfo | None:
        orm = self._db.query(GroupORM).filter(GroupORM.group_code == group_code).first()
        return _group_to_domain(orm) if orm else None

    def list_groups(self, *, accessible_ids=None, keyword=None, status=None, region_code=None, page=1, page_size=10) -> tuple[list[GroupInfo], int]:
        from sqlalchemy import or_
        query = self._db.query(GroupORM)
        if accessible_ids is not None:
            query = query.filter(GroupORM.id.in_(accessible_ids))
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(GroupORM.group_code.like(like), GroupORM.group_name.like(like)))
        if status:
            query = query.filter(GroupORM.status == status)
        if region_code:
            query = query.filter(GroupORM.region_code == region_code)
        total = query.count()
        items = query.order_by(GroupORM.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return [_group_to_domain(i) for i in items], total

    def save(self, group: GroupInfo) -> GroupInfo:
        if group.id is not None:
            orm = self._db.query(GroupORM).filter(GroupORM.id == group.id).first()
            if orm:
                for attr in ["group_name", "group_level", "region_code", "region_name", "lead_agency_id",
                             "description", "status", "approval_required", "approval_status", "approval_agency_id",
                             "approved_by", "approved_at", "rejected_by", "rejected_at", "reject_reason",
                             "activated_at", "dissolved_at", "dissolve_reason",
                             "delete_approval_status", "delete_approval_agency_id",
                             "delete_requested_by", "delete_requested_at",
                             "delete_approved_by", "delete_approved_at",
                             "delete_rejected_by", "delete_rejected_at", "delete_reject_reason"]:
                    setattr(orm, attr, getattr(group, attr))
                orm.updated_at = datetime.now()
                self._db.flush()
                self._db.refresh(orm)
                return _group_to_domain(orm)
        orm = GroupORM(
            group_code=group.group_code, group_name=group.group_name,
            group_level=group.group_level, region_code=group.region_code, region_name=group.region_name,
            lead_agency_id=group.lead_agency_id, description=group.description, status=group.status,
            created_by=group.created_by, creator_agency_id=group.creator_agency_id,
            approval_required=group.approval_required, approval_status=group.approval_status,
            approval_agency_id=group.approval_agency_id,
        )
        self._db.add(orm)
        self._db.flush()
        self._db.refresh(orm)
        return _group_to_domain(orm)

    def delete(self, group_id: int) -> None:
        self._db.query(GroupNodeORM).filter(GroupNodeORM.group_id == group_id).delete()
        self._db.query(SysUserGroup).filter(SysUserGroup.group_id == group_id).delete()
        self._db.query(GroupMemberORM).filter(GroupMemberORM.group_id == group_id).delete()
        self._db.query(GroupLifecycleLog).filter(GroupLifecycleLog.group_id == group_id).delete()
        g = self._db.query(GroupORM).filter(GroupORM.id == group_id).first()
        if g:
            self._db.delete(g)
        self._db.flush()

    def count_members(self, group_id: int) -> int:
        return self._db.query(GroupMemberORM).filter(GroupMemberORM.group_id == group_id, GroupMemberORM.join_status == "active").count()

    def count_users(self, group_id: int) -> int:
        return self._db.query(SysUserGroup).filter(SysUserGroup.group_id == group_id, SysUserGroup.join_status == "active").count()

    def count_nodes(self, group_id: int) -> int:
        return self._db.query(GroupNodeORM).filter(GroupNodeORM.group_id == group_id, GroupNodeORM.auth_status == "active").count()

    def count_tasks(self, group_id: int) -> int:
        from app.models.task import Task
        return self._db.query(Task).filter(Task.group_id == group_id).count()


class SQLAlchemyGroupMemberRepository(GroupMemberRepository):
    def __init__(self, db: Session):
        self._db = db

    def list_members(self, group_id: int) -> list[GroupMember]:
        orms = self._db.query(GroupMemberORM).filter(GroupMemberORM.group_id == group_id).order_by(GroupMemberORM.is_lead.desc()).all()
        return [_member_to_domain(o) for o in orms]

    def get_member(self, group_id: int, agency_id: int) -> GroupMember | None:
        orm = self._db.query(GroupMemberORM).filter(GroupMemberORM.group_id == group_id, GroupMemberORM.agency_id == agency_id).first()
        return _member_to_domain(orm) if orm else None

    def save_member(self, member: GroupMember) -> GroupMember:
        if member.id is not None:
            orm = self._db.query(GroupMemberORM).filter(GroupMemberORM.id == member.id).first()
            if orm:
                for attr in ["member_role", "is_lead", "join_status", "joined_at", "removed_at"]:
                    setattr(orm, attr, getattr(member, attr))
                orm.updated_at = datetime.now()
                self._db.flush()
                return _member_to_domain(orm)
        orm = GroupMemberORM(
            group_id=member.group_id, agency_id=member.agency_id,
            member_role=member.member_role, is_lead=member.is_lead,
            join_status=member.join_status, joined_at=member.joined_at or datetime.now(),
        )
        self._db.add(orm)
        self._db.flush()
        return _member_to_domain(orm)

    def remove_member(self, group_id: int, agency_id: int) -> None:
        orm = self._db.query(GroupMemberORM).filter(GroupMemberORM.group_id == group_id, GroupMemberORM.agency_id == agency_id).first()
        if orm:
            orm.join_status = "removed"
            orm.removed_at = datetime.now()
            self._db.flush()


class BridgeGroupNodeRepository(GroupNodeRepository):
    def __init__(self, db: Session):
        self._db = db
        self._current_user = None

    def set_current_user(self, user):
        self._current_user = user

    def list_nodes(self, group_id: int, node_type=None, node_usage_role=None, auth_status=None) -> list[dict]:
        from app.services.group_service import list_group_nodes as _list
        items = _list(self._db, group_id, self._current_user, node_type=node_type, node_usage_role=node_usage_role, auth_status=auth_status)
        return items if isinstance(items, list) else []

    def list_available_nodes(self, group_id: int, visible_agency_ids=None) -> list[dict]:
        from app.services.group_service import list_available_group_nodes as _list
        return _list(self._db, group_id, self._current_user) or []

    def get_node_auth(self, group_id: int, node_id: int) -> GroupNodeAuth | None:
        orm = self._db.query(GroupNodeORM).filter(GroupNodeORM.group_id == group_id, GroupNodeORM.node_id == node_id).first()
        if not orm:
            return None
        return GroupNodeAuth(id=orm.id, group_id=orm.group_id, agency_id=orm.agency_id, node_id=orm.node_id,
                             node_usage_role=orm.node_usage_role, auth_status=orm.auth_status)

    def save_node_auth(self, auth: GroupNodeAuth) -> GroupNodeAuth:
        if auth.id is not None:
            orm = self._db.query(GroupNodeORM).filter(GroupNodeORM.id == auth.id).first()
            if orm:
                for attr in ["node_usage_role", "auth_status", "authorized_at", "revoked_at"]:
                    setattr(orm, attr, getattr(auth, attr))
                orm.updated_at = datetime.now()
                self._db.flush()
                return auth
        return auth

    def remove_node_auth(self, group_id: int, node_id: int) -> None:
        orm = self._db.query(GroupNodeORM).filter(GroupNodeORM.group_id == group_id, GroupNodeORM.node_id == node_id).first()
        if orm:
            orm.auth_status = "revoked"
            orm.revoked_at = datetime.now()
            self._db.flush()


class BridgeGroupDatasetRepository(GroupDatasetRepository):
    def __init__(self, db: Session):
        self._db = db

    def list_datasets(self, group_id: int) -> list[dict]:
        auths = self._db.query(GroupDatasetORM).filter(GroupDatasetORM.group_id == group_id, GroupDatasetORM.auth_status == "active").all()
        result = []
        for a in auths:
            ds = self._db.query(DatasetORM).filter(DatasetORM.id == a.dataset_id).first()
            agency = self._db.query(Agency).filter(Agency.id == a.agency_id).first() if a.agency_id else None
            result.append({
                "id": a.id, "group_id": a.group_id, "agency_id": a.agency_id,
                "agency_name": agency.agency_name if agency else None,
                "dataset_id": a.dataset_id, "dataset_name": ds.dataset_name if ds else None,
                "dataset_code": ds.dataset_code if ds else None,
                "auth_status": a.auth_status, "authorized_at": _format_dt(a.authorized_at),
                "created_at": _format_dt(a.created_at),
            })
        return result

    def list_available_datasets(self, group_id: int, visible_agency_ids=None) -> list[dict]:
        authed_ids = [a.dataset_id for a in self._db.query(GroupDatasetORM).filter(GroupDatasetORM.group_id == group_id, GroupDatasetORM.auth_status == "active").all()]
        query = self._db.query(DatasetORM).filter(DatasetORM.status == "enabled")
        if authed_ids:
            query = query.filter(DatasetORM.id.notin_(authed_ids))
        if visible_agency_ids is not None:
            query = query.filter(DatasetORM.agency_id.in_(visible_agency_ids))
        datasets = query.order_by(DatasetORM.id.asc()).all()
        result = []
        for ds in datasets:
            agency = self._db.query(Agency).filter(Agency.id == ds.agency_id).first()
            result.append({
                "id": ds.id, "dataset_code": ds.dataset_code, "dataset_name": ds.dataset_name,
                "agency_id": ds.agency_id, "agency_name": agency.agency_name if agency else None,
                "data_type": ds.data_type, "status": ds.status,
            })
        return result

    def get_dataset_auth(self, group_id: int, dataset_id: int) -> GroupDatasetAuth | None:
        orm = self._db.query(GroupDatasetORM).filter(GroupDatasetORM.group_id == group_id, GroupDatasetORM.dataset_id == dataset_id).first()
        if not orm:
            return None
        return GroupDatasetAuth(id=orm.id, group_id=orm.group_id, agency_id=orm.agency_id, dataset_id=orm.dataset_id, auth_status=orm.auth_status)

    def save_dataset_auth(self, auth: GroupDatasetAuth) -> GroupDatasetAuth:
        if auth.id is not None:
            orm = self._db.query(GroupDatasetORM).filter(GroupDatasetORM.id == auth.id).first()
            if orm:
                for attr in ["auth_status", "authorized_at", "revoked_at"]:
                    setattr(orm, attr, getattr(auth, attr))
                self._db.flush()
                return auth
        orm = GroupDatasetORM(
            group_id=auth.group_id, agency_id=auth.agency_id, dataset_id=auth.dataset_id,
            auth_status=auth.auth_status, authorized_by=auth.authorized_by, authorized_at=auth.authorized_at or datetime.now(),
        )
        self._db.add(orm)
        self._db.flush()
        auth.id = orm.id
        return auth

    def remove_dataset_auth(self, group_id: int, dataset_id: int) -> None:
        orm = self._db.query(GroupDatasetORM).filter(GroupDatasetORM.group_id == group_id, GroupDatasetORM.dataset_id == dataset_id).first()
        if orm:
            orm.auth_status = "revoked"
            orm.revoked_at = datetime.now()
            self._db.flush()


class BridgeGroupTemplateRepository(GroupTemplateRepository):
    def __init__(self, db: Session):
        self._db = db

    def list_templates(self, group_id: int) -> list[dict]:
        auths = self._db.query(GroupTemplateORM).filter(GroupTemplateORM.group_id == group_id, GroupTemplateORM.auth_status == "active").all()
        result = []
        for a in auths:
            t = self._db.query(TemplateORM).filter(TemplateORM.id == a.template_id).first()
            agency = self._db.query(Agency).filter(Agency.id == a.agency_id).first() if a.agency_id else None
            result.append({
                "id": a.id, "group_id": a.group_id, "agency_id": a.agency_id,
                "agency_name": agency.agency_name if agency else None,
                "template_id": a.template_id, "template_name": t.template_name if t else None,
                "template_code": t.template_code if t else None,
                "auth_status": a.auth_status, "authorized_at": _format_dt(a.authorized_at),
                "created_at": _format_dt(a.created_at),
            })
        return result

    def list_available_templates(self, group_id: int, visible_agency_ids=None) -> list[dict]:
        authed_ids = [a.template_id for a in self._db.query(GroupTemplateORM).filter(GroupTemplateORM.group_id == group_id, GroupTemplateORM.auth_status == "active").all()]
        query = self._db.query(TemplateORM).filter(TemplateORM.status == "enabled")
        if authed_ids:
            query = query.filter(TemplateORM.id.notin_(authed_ids))
        if visible_agency_ids is not None:
            query = query.filter((TemplateORM.agency_id.in_(visible_agency_ids)) | (TemplateORM.agency_id.is_(None)))
        templates = query.order_by(TemplateORM.id.asc()).all()
        result = []
        for t in templates:
            agency = self._db.query(Agency).filter(Agency.id == t.agency_id).first() if t.agency_id else None
            result.append({
                "id": t.id, "template_code": t.template_code, "template_name": t.template_name,
                "agency_id": t.agency_id, "agency_name": agency.agency_name if agency else None,
                "scenario": t.scenario, "status": t.status,
            })
        return result

    def get_template_auth(self, group_id: int, template_id: int) -> GroupTemplateAuth | None:
        orm = self._db.query(GroupTemplateORM).filter(GroupTemplateORM.group_id == group_id, GroupTemplateORM.template_id == template_id).first()
        if not orm:
            return None
        return GroupTemplateAuth(id=orm.id, group_id=orm.group_id, agency_id=orm.agency_id, template_id=orm.template_id, auth_status=orm.auth_status)

    def save_template_auth(self, auth: GroupTemplateAuth) -> GroupTemplateAuth:
        if auth.id is not None:
            orm = self._db.query(GroupTemplateORM).filter(GroupTemplateORM.id == auth.id).first()
            if orm:
                for attr in ["auth_status", "authorized_at", "revoked_at"]:
                    setattr(orm, attr, getattr(auth, attr))
                self._db.flush()
                return auth
        orm = GroupTemplateORM(
            group_id=auth.group_id, agency_id=auth.agency_id, template_id=auth.template_id,
            auth_status=auth.auth_status, authorized_by=auth.authorized_by, authorized_at=auth.authorized_at or datetime.now(),
        )
        self._db.add(orm)
        self._db.flush()
        auth.id = orm.id
        return auth

    def remove_template_auth(self, group_id: int, template_id: int) -> None:
        orm = self._db.query(GroupTemplateORM).filter(GroupTemplateORM.group_id == group_id, GroupTemplateORM.template_id == template_id).first()
        if orm:
            orm.auth_status = "revoked"
            orm.revoked_at = datetime.now()
            self._db.flush()


class BridgeAccessControlPort(AccessControlPort):
    def __init__(self, db: Session):
        self._db = db

    def get_accessible_group_ids(self, current_user) -> list[int] | None:
        from app.services.access_control_service import get_accessible_group_ids
        return get_accessible_group_ids(self._db, current_user.id)

    def check_group_access(self, current_user, group_id: int) -> None:
        from app.services.access_control_service import check_group_access
        check_group_access(self._db, current_user.id, group_id)

    def check_group_admin_access(self, current_user, group_id: int) -> None:
        from app.services.access_control_service import check_group_admin_access
        check_group_admin_access(self._db, current_user.id, group_id)

    def is_platform_admin(self, user_id: int) -> bool:
        from app.services.access_control_service import is_platform_admin
        return is_platform_admin(self._db, user_id)

    def is_agency_admin(self, user_id: int) -> bool:
        from app.services.access_control_service import is_agency_admin
        return is_agency_admin(self._db, user_id)

    def get_visible_agency_ids(self, current_user) -> list[int] | None:
        from app.services.access_control_service import is_platform_admin, is_agency_admin
        if is_platform_admin(self._db, current_user.id):
            return None
        user_agency_id = current_user.agency_id
        if not user_agency_id:
            return []
        agency_ids = [user_agency_id]
        if is_agency_admin(self._db, current_user.id):
            def collect(parent_id: int):
                children = self._db.query(Agency.id).filter(Agency.parent_agency_id == parent_id, Agency.status == "active").all()
                for child in children:
                    cid = child[0]
                    if cid not in agency_ids:
                        agency_ids.append(cid)
                        collect(cid)
            collect(user_agency_id)
        return agency_ids

    def can_approve_group(self, current_user, group) -> bool:
        from app.services.access_control_service import can_approve_group
        return can_approve_group(self._db, current_user.id, group)

    def find_common_parent_agency(self, agency_id_1: int, agency_id_2: int) -> int | None:
        from app.services.access_control_service import find_common_parent_agency
        return find_common_parent_agency(self._db, agency_id_1, agency_id_2)


class BridgeAuditLogPort(AuditLogPort):
    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type=None, resource_id=None, agency_id=None, group_id=None, request=None) -> None:
        from app.services.access_control_service import write_operate_log
        write_operate_log(db=db, user_id=user_id, username=username, operation_type=operation_type,
                          resource_type=resource_type, resource_id=resource_id, agency_id=agency_id, group_id=group_id, request=request)

    def write_lifecycle_log(self, db, group_id, event_type, operator_user_id, operator_name, before_status=None, after_status=None, reason=None) -> None:
        log = GroupLifecycleLog(
            group_id=group_id, event_type=event_type, before_status=before_status, after_status=after_status,
            operator_user_id=operator_user_id, operator_name=operator_name, reason=reason,
        )
        db.add(log)
        db.flush()


class BridgeUserQueryPort(UserQueryPort):
    def __init__(self, db: Session):
        self._db = db
        self._current_user = None

    def set_current_user(self, user):
        self._current_user = user

    def list_group_users(self, group_id: int) -> list[dict]:
        from app.services.group_service import list_group_users as _list
        return _list(self._db, group_id, self._current_user) or []

    def add_group_user(self, group_id: int, user_id: int, role_code: str, current_user) -> dict:
        from app.services.group_service import add_group_user as _add
        return _add(self._db, group_id, {"user_id": user_id, "role_code": role_code}, current_user)

    def update_group_user_role(self, group_id: int, user_id: int, role_code: str, current_user) -> dict:
        from app.services.group_service import update_group_user_role as _update
        return _update(self._db, group_id, user_id, {"role_code": role_code}, current_user)

    def remove_group_user(self, group_id: int, user_id: int, current_user) -> dict:
        from app.services.group_service import remove_group_user as _remove
        return _remove(self._db, group_id, user_id, current_user)


class BridgeAgencyQueryPort(AgencyQueryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_agency_name(self, agency_id: int | None) -> str | None:
        if not agency_id:
            return None
        a = self._db.query(Agency).filter(Agency.id == agency_id).first()
        return a.agency_name if a else None

    def get_agency_by_id(self, agency_id: int):
        return self._db.query(Agency).filter(Agency.id == agency_id).first()


class BridgeLifecycleLogRepository(LifecycleLogRepository):
    def __init__(self, db: Session):
        self._db = db

    def list_logs(self, group_id: int) -> list[dict]:
        from app.services.group_lifecycle_service import GroupLifecycleService
        return GroupLifecycleService.list_lifecycle_logs(self._db, group_id) or []
