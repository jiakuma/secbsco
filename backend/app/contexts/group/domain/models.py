from dataclasses import dataclass, field
from datetime import datetime
from .enums import GroupStatus, ApprovalStatus, MemberRole, JoinStatus, NodeUsageRole, AuthStatus


@dataclass
class GroupInfo:
    id: int | None = None
    group_code: str = ""
    group_name: str = ""
    group_level: str | None = None
    region_code: str | None = None
    region_name: str | None = None
    lead_agency_id: int | None = None
    description: str | None = None
    status: str = "draft"
    created_by: int | None = None
    creator_agency_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    approval_required: bool = False
    approval_status: str = "none"
    approval_agency_id: int | None = None
    approved_by: int | None = None
    approved_at: datetime | None = None
    rejected_by: int | None = None
    rejected_at: datetime | None = None
    reject_reason: str | None = None
    activated_at: datetime | None = None
    dissolved_at: datetime | None = None
    dissolve_reason: str | None = None
    delete_approval_status: str = "none"
    delete_approval_agency_id: int | None = None
    delete_requested_by: int | None = None
    delete_requested_at: datetime | None = None
    delete_approved_by: int | None = None
    delete_approved_at: datetime | None = None
    delete_rejected_by: int | None = None
    delete_rejected_at: datetime | None = None
    delete_reject_reason: str | None = None

    def submit_for_approval(self) -> None:
        self.status = GroupStatus.PENDING_APPROVAL.value
        self.approval_status = ApprovalStatus.PENDING.value
        self.approval_required = True

    def approve(self, approver_id: int) -> None:
        self.approval_status = ApprovalStatus.APPROVED.value
        self.approved_by = approver_id
        self.approved_at = datetime.now()
        self.status = GroupStatus.DRAFT.value

    def reject(self, rejector_id: int, reason: str) -> None:
        self.approval_status = ApprovalStatus.REJECTED.value
        self.rejected_by = rejector_id
        self.rejected_at = datetime.now()
        self.reject_reason = reason
        self.status = GroupStatus.REJECTED.value

    def activate(self) -> None:
        self.status = GroupStatus.ACTIVE.value
        self.activated_at = datetime.now()

    def submit_dissolving(self) -> None:
        self.status = GroupStatus.DISSOLVING.value
        self.delete_approval_status = ApprovalStatus.PENDING.value

    def reject_dissolving(self, reason: str) -> None:
        self.status = GroupStatus.ACTIVE.value
        self.delete_approval_status = ApprovalStatus.REJECTED.value
        self.delete_reject_reason = reason
        self.delete_rejected_at = datetime.now()

    def is_editable(self) -> bool:
        return self.status not in {
            GroupStatus.ARCHIVED.value, GroupStatus.REJECTED.value,
            GroupStatus.DISSOLVED.value,
        }

    def is_pending_approval(self) -> bool:
        return self.status == GroupStatus.PENDING_APPROVAL.value and self.approval_status == ApprovalStatus.PENDING.value

    def is_dissolving_pending(self) -> bool:
        return self.status == GroupStatus.DISSOLVING.value and self.delete_approval_status == ApprovalStatus.PENDING.value


@dataclass
class GroupMember:
    id: int | None = None
    group_id: int | None = None
    agency_id: int | None = None
    member_role: str = "participant"
    is_lead: bool = False
    join_status: str = "active"
    joined_at: datetime | None = None
    removed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def rejoin(self) -> None:
        self.join_status = JoinStatus.ACTIVE.value
        self.joined_at = datetime.now()
        self.removed_at = None

    def remove(self) -> None:
        self.join_status = JoinStatus.REMOVED.value
        self.removed_at = datetime.now()


@dataclass
class GroupNodeAuth:
    id: int | None = None
    group_id: int | None = None
    agency_id: int | None = None
    node_id: int | None = None
    node_usage_role: str = "group_service"
    auth_status: str = "active"
    resource_quota_json: dict | None = None
    priority_level: int = 1
    max_concurrent_tasks: int = 1
    authorized_by: int | None = None
    authorized_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def revoke(self) -> None:
        self.auth_status = AuthStatus.REVOKED.value
        self.revoked_at = datetime.now()

    def reactivate(self) -> None:
        self.auth_status = AuthStatus.ACTIVE.value
        self.authorized_at = datetime.now()
        self.revoked_at = None


@dataclass
class GroupDatasetAuth:
    id: int | None = None
    group_id: int | None = None
    agency_id: int | None = None
    dataset_id: int | None = None
    auth_status: str = "active"
    authorized_by: int | None = None
    authorized_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def revoke(self) -> None:
        self.auth_status = AuthStatus.REVOKED.value
        self.revoked_at = datetime.now()

    def reactivate(self) -> None:
        self.auth_status = AuthStatus.ACTIVE.value
        self.authorized_at = datetime.now()
        self.revoked_at = None


@dataclass
class GroupTemplateAuth:
    id: int | None = None
    group_id: int | None = None
    agency_id: int | None = None
    template_id: int | None = None
    auth_status: str = "active"
    authorized_by: int | None = None
    authorized_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def revoke(self) -> None:
        self.auth_status = AuthStatus.REVOKED.value
        self.revoked_at = datetime.now()

    def reactivate(self) -> None:
        self.auth_status = AuthStatus.ACTIVE.value
        self.authorized_at = datetime.now()
        self.revoked_at = None
