from dataclasses import asdict
from datetime import datetime
from ..domain.models import GroupInfo, GroupMember, GroupNodeAuth, GroupDatasetAuth, GroupTemplateAuth
from ..domain.ports import (
    GroupRepository, GroupMemberRepository, GroupNodeRepository,
    GroupDatasetRepository, GroupTemplateRepository,
    AccessControlPort, AuditLogPort, UserQueryPort, AgencyQueryPort, LifecycleLogRepository,
)
from ..domain.exceptions import (
    GroupNotFound, GroupNotEditable, GroupNotPendingApproval, GroupNotDissolving,
    CannotRemoveLeadAgency, MemberHasNodes, GroupHasRunningTasks,
    CannotApproveGroup, GroupAccessDenied,
)
from .dtos import GroupDTO, PaginatedGroupsDTO, GroupMemberDTO


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _to_group_dto(g: GroupInfo, agency_name: str | None = None, *,
                  member_count=0, user_count=0, node_count=0, task_count=0,
                  can_delete=False, need_delete_approval=False, can_approve_delete=False) -> GroupDTO:
    return GroupDTO(
        id=g.id, group_code=g.group_code, group_name=g.group_name,
        group_level=g.group_level, region_code=g.region_code, region_name=g.region_name,
        lead_agency_id=g.lead_agency_id, lead_agency_name=agency_name,
        description=g.description, status=g.status,
        approval_required=g.approval_required, approval_status=g.approval_status,
        member_count=member_count, user_count=user_count, node_count=node_count, task_count=task_count,
        can_delete=can_delete, need_delete_approval=need_delete_approval, can_approve_delete=can_approve_delete,
        created_by=g.created_by, creator_agency_id=g.creator_agency_id,
        created_at=_format_dt(g.created_at), updated_at=_format_dt(g.updated_at),
    )


class ListGroupsUseCase:
    def __init__(self, repo: GroupRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, current_user, **filters) -> PaginatedGroupsDTO:
        accessible_ids = self._access_control.get_accessible_group_ids(current_user)
        groups, total = self._repo.list_groups(accessible_ids=accessible_ids, **filters)
        items = []
        for g in groups:
            agency_name = self._agency.get_agency_name(g.lead_agency_id)
            items.append(_to_group_dto(g, agency_name,
                member_count=self._repo.count_members(g.id),
                user_count=self._repo.count_users(g.id),
                node_count=self._repo.count_nodes(g.id)))
        return PaginatedGroupsDTO(total=total, page=filters.get("page", 1), page_size=filters.get("page_size", 10), items=items)


class GetGroupDetailUseCase:
    def __init__(self, repo: GroupRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, group_id: int, current_user) -> dict:
        self._access_control.check_group_access(current_user, group_id)
        g = self._repo.get_by_id(group_id)
        if not g:
            raise GroupNotFound()
        agency_name = self._agency.get_agency_name(g.lead_agency_id)
        dto = _to_group_dto(g, agency_name)
        result = asdict(dto)
        result["summary"] = {
            "member_count": self._repo.count_members(g.id),
            "user_count": self._repo.count_users(g.id),
            "node_count": self._repo.count_nodes(g.id),
            "task_count": self._repo.count_tasks(g.id),
        }
        return result


class CreateGroupUseCase:
    def __init__(self, repo: GroupRepository, member_repo: GroupMemberRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._member_repo = member_repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, payload: dict, current_user, db=None, request=None) -> GroupDTO:
        is_platform = self._access_control.is_platform_admin(current_user.id)
        is_agency = self._access_control.is_agency_admin(current_user.id)
        if not is_platform and not is_agency:
            raise GroupAccessDenied()
        lead_agency_id = payload.get("lead_agency_id", current_user.agency_id)
        member_agency_ids = payload.get("member_agency_ids", [])
        needs_approval = not is_platform and self._has_same_level_member(lead_agency_id, member_agency_ids, current_user)
        group = GroupInfo(
            group_code=payload.get("group_code"), group_name=payload.get("group_name"),
            group_level=payload.get("group_level", "city"),
            region_code=payload.get("region_code"), region_name=payload.get("region_name"),
            lead_agency_id=lead_agency_id, description=payload.get("description"),
            created_by=current_user.id, creator_agency_id=current_user.agency_id,
        )
        if needs_approval:
            group.submit_for_approval()
            common_parent = self._access_control.find_common_parent_agency(lead_agency_id, member_agency_ids[0] if member_agency_ids else lead_agency_id)
            group.approval_agency_id = common_parent
        else:
            group.activate()
        group = self._repo.save(group)
        lead_member = GroupMember(group_id=group.id, agency_id=lead_agency_id, member_role="lead_agency", is_lead=True)
        self._member_repo.save_member(lead_member)
        for mid in member_agency_ids:
            if mid != lead_agency_id:
                m = GroupMember(group_id=group.id, agency_id=mid, member_role="participant", is_lead=False)
                self._member_repo.save_member(m)
        if db:
            self._audit.write_lifecycle_log(db, group.id, "create", current_user.id, current_user.username, after_status=group.status)
            self._audit.write_operate_log(db=db, user_id=current_user.id, username=current_user.username,
                operation_type="GROUP_CREATE", resource_type="group", resource_id=group.id, agency_id=lead_agency_id, request=request)
        agency_name = self._agency.get_agency_name(lead_agency_id)
        return _to_group_dto(group, agency_name, member_count=1 + len([m for m in member_agency_ids if m != lead_agency_id]))

    def _has_same_level_member(self, lead_agency_id, member_agency_ids, current_user) -> bool:
        for mid in member_agency_ids:
            if mid != lead_agency_id:
                return True
        return False


class UpdateGroupUseCase:
    def __init__(self, repo: GroupRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, group_id: int, payload: dict, current_user, db=None, request=None) -> GroupDTO:
        self._access_control.check_group_admin_access(current_user, group_id)
        g = self._repo.get_by_id(group_id)
        if not g:
            raise GroupNotFound()
        if not g.is_editable():
            raise GroupNotEditable()
        for field in ["group_name", "group_level", "region_code", "region_name", "description"]:
            if field in payload and payload[field] is not None:
                setattr(g, field, payload[field])
        g.updated_at = datetime.now()
        g = self._repo.save(g)
        if db:
            self._audit.write_operate_log(db=db, user_id=current_user.id, username=current_user.username,
                operation_type="GROUP_UPDATE", resource_type="group", resource_id=g.id, request=request)
        return _to_group_dto(g, self._agency.get_agency_name(g.lead_agency_id))


class ApproveGroupUseCase:
    def __init__(self, repo: GroupRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, group_id: int, payload: dict, current_user, db=None, request=None) -> GroupDTO:
        g = self._repo.get_by_id(group_id)
        if not g:
            raise GroupNotFound()
        if not g.is_pending_approval():
            raise GroupNotPendingApproval()
        if not self._access_control.can_approve_group(current_user, g):
            raise CannotApproveGroup()
        g.approve(current_user.id)
        g = self._repo.save(g)
        if db:
            self._audit.write_lifecycle_log(db, g.id, "approve", current_user.id, current_user.username, before_status="pending_approval", after_status=g.status)
            self._audit.write_operate_log(db=db, user_id=current_user.id, username=current_user.username,
                operation_type="GROUP_APPROVE", resource_type="group", resource_id=g.id, request=request)
        return _to_group_dto(g, self._agency.get_agency_name(g.lead_agency_id))


class RejectGroupUseCase:
    def __init__(self, repo: GroupRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, group_id: int, payload: dict, current_user, db=None, request=None) -> GroupDTO:
        g = self._repo.get_by_id(group_id)
        if not g:
            raise GroupNotFound()
        if not g.is_pending_approval():
            raise GroupNotPendingApproval()
        if not self._access_control.can_approve_group(current_user, g):
            raise CannotApproveGroup()
        g.reject(current_user.id, payload.get("reason", ""))
        g = self._repo.save(g)
        if db:
            self._audit.write_lifecycle_log(db, g.id, "reject", current_user.id, current_user.username, before_status="pending_approval", after_status=g.status)
            self._audit.write_operate_log(db=db, user_id=current_user.id, username=current_user.username,
                operation_type="GROUP_REJECT", resource_type="group", resource_id=g.id, request=request)
        return _to_group_dto(g, self._agency.get_agency_name(g.lead_agency_id))


class ListMembersUseCase:
    def __init__(self, member_repo: GroupMemberRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._member_repo = member_repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, group_id: int, current_user) -> list[GroupMemberDTO]:
        self._access_control.check_group_access(current_user, group_id)
        members = self._member_repo.list_members(group_id)
        return [GroupMemberDTO(
            id=m.id, group_id=m.group_id, agency_id=m.agency_id,
            agency_name=self._agency.get_agency_name(m.agency_id),
            member_role=m.member_role, is_lead=m.is_lead,
            join_status=m.join_status, joined_at=_format_dt(m.joined_at),
            created_at=_format_dt(m.created_at),
        ) for m in members if m.join_status == "active"]


class AddMemberUseCase:
    def __init__(self, member_repo: GroupMemberRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._member_repo = member_repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, group_id: int, payload: dict, current_user, db=None, request=None) -> GroupMemberDTO:
        self._access_control.check_group_admin_access(current_user, group_id)
        agency_id = payload.get("agency_id")
        existing = self._member_repo.get_member(group_id, agency_id)
        if existing and existing.join_status == "active":
            from ..domain.exceptions import MemberAlreadyExists
            raise MemberAlreadyExists()
        if existing:
            existing.rejoin()
            self._member_repo.save_member(existing)
            m = existing
        else:
            m = GroupMember(group_id=group_id, agency_id=agency_id, member_role=payload.get("member_type", "participant"), is_lead=False)
            m = self._member_repo.save_member(m)
        if db:
            self._audit.write_operate_log(db=db, user_id=current_user.id, username=current_user.username,
                operation_type="GROUP_ADD_MEMBER", resource_type="group", resource_id=group_id, request=request)
        return GroupMemberDTO(id=m.id, group_id=m.group_id, agency_id=m.agency_id,
            agency_name=self._agency.get_agency_name(m.agency_id), member_role=m.member_role, is_lead=m.is_lead)


class RemoveMemberUseCase:
    def __init__(self, member_repo: GroupMemberRepository, node_repo: GroupNodeRepository, access_control: AccessControlPort, audit: AuditLogPort):
        self._member_repo = member_repo
        self._node_repo = node_repo
        self._access_control = access_control
        self._audit = audit

    def execute(self, group_id: int, agency_id: int, current_user, db=None, request=None) -> dict:
        self._access_control.check_group_admin_access(current_user, group_id)
        member = self._member_repo.get_member(group_id, agency_id)
        if not member:
            raise GroupNotFound()
        if member.is_lead:
            raise CannotRemoveLeadAgency()
        self._member_repo.remove_member(group_id, agency_id)
        if db:
            self._audit.write_operate_log(db=db, user_id=current_user.id, username=current_user.username,
                operation_type="GROUP_REMOVE_MEMBER", resource_type="group", resource_id=group_id, request=request)
        return {"removed": True}


class RequestDeleteGroupUseCase:
    def __init__(self, repo: GroupRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, group_id: int, current_user, db=None, request=None) -> GroupDTO:
        self._access_control.check_group_admin_access(current_user, group_id)
        g = self._repo.get_by_id(group_id)
        if not g:
            raise GroupNotFound()
        is_platform = self._access_control.is_platform_admin(current_user.id)
        if is_platform:
            self._repo.delete(group_id)
            return _to_group_dto(g, self._agency.get_agency_name(g.lead_agency_id))
        g.submit_dissolving()
        g.delete_requested_by = current_user.id
        g.delete_requested_at = datetime.now()
        g = self._repo.save(g)
        if db:
            self._audit.write_lifecycle_log(db, g.id, "request_delete", current_user.id, current_user.username, before_status="active", after_status="dissolving")
            self._audit.write_operate_log(db=db, user_id=current_user.id, username=current_user.username,
                operation_type="GROUP_REQUEST_DELETE", resource_type="group", resource_id=g.id, request=request)
        return _to_group_dto(g, self._agency.get_agency_name(g.lead_agency_id))


class ApproveDeleteGroupUseCase:
    def __init__(self, repo: GroupRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, group_id: int, current_user, db=None, request=None) -> GroupDTO:
        g = self._repo.get_by_id(group_id)
        if not g:
            raise GroupNotFound()
        if not g.is_dissolving_pending():
            raise GroupNotDissolving()
        g.delete_approved_by = current_user.id
        g.delete_approved_at = datetime.now()
        self._repo.delete(group_id)
        if db:
            self._audit.write_operate_log(db=db, user_id=current_user.id, username=current_user.username,
                operation_type="GROUP_APPROVE_DELETE", resource_type="group", resource_id=group_id, request=request)
        return _to_group_dto(g, self._agency.get_agency_name(g.lead_agency_id))


class RejectDeleteGroupUseCase:
    def __init__(self, repo: GroupRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, group_id: int, reason: str, current_user, db=None, request=None) -> GroupDTO:
        g = self._repo.get_by_id(group_id)
        if not g:
            raise GroupNotFound()
        if not g.is_dissolving_pending():
            raise GroupNotDissolving()
        g.reject_dissolving(reason)
        g.delete_rejected_by = current_user.id
        g = self._repo.save(g)
        if db:
            self._audit.write_lifecycle_log(db, g.id, "reject_delete", current_user.id, current_user.username, before_status="dissolving", after_status="active")
            self._audit.write_operate_log(db=db, user_id=current_user.id, username=current_user.username,
                operation_type="GROUP_REJECT_DELETE", resource_type="group", resource_id=g.id, request=request)
        return _to_group_dto(g, self._agency.get_agency_name(g.lead_agency_id))


class ListVisibleGroupsForTaskUseCase:
    def __init__(self, repo: GroupRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, current_user) -> list[dict]:
        accessible_ids = self._access_control.get_accessible_group_ids(current_user)
        if accessible_ids is None:
            groups, _ = self._repo.list_groups(page=1, page_size=10000)
        elif not accessible_ids:
            return []
        else:
            groups, _ = self._repo.list_groups(accessible_ids=accessible_ids, page=1, page_size=10000)
        return [{"id": g.id, "group_name": g.group_name, "status": g.status} for g in groups if g.status == "active"]
