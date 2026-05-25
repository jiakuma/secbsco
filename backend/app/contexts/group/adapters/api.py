from dataclasses import asdict
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.utils.response import success
from .persistence import (
    SQLAlchemyGroupRepository, SQLAlchemyGroupMemberRepository,
    BridgeGroupNodeRepository, BridgeGroupDatasetRepository, BridgeGroupTemplateRepository,
    BridgeAccessControlPort, BridgeAuditLogPort, BridgeUserQueryPort, BridgeAgencyQueryPort, BridgeLifecycleLogRepository,
)
from .schemas import (
    GroupCreate, GroupUpdate, GroupApprove, GroupReject,
    AddGroupMember, AddGroupUser, UpdateGroupUserRole, AddGroupNode, RejectDeleteRequest,
)
from ..application.use_cases import (
    ListGroupsUseCase, GetGroupDetailUseCase, CreateGroupUseCase, UpdateGroupUseCase,
    ApproveGroupUseCase, RejectGroupUseCase, ListMembersUseCase, AddMemberUseCase, RemoveMemberUseCase,
    RequestDeleteGroupUseCase, ApproveDeleteGroupUseCase, RejectDeleteGroupUseCase,
    ListVisibleGroupsForTaskUseCase,
)
from ..application.dtos import GroupMemberDTO


router = APIRouter(prefix="/api/groups", tags=["群组管理"])


def _repos(db: Session):
    return (
        SQLAlchemyGroupRepository(db), SQLAlchemyGroupMemberRepository(db),
        BridgeGroupNodeRepository(db), BridgeGroupDatasetRepository(db), BridgeGroupTemplateRepository(db),
        BridgeAccessControlPort(db), BridgeAuditLogPort(), BridgeUserQueryPort(db), BridgeAgencyQueryPort(db), BridgeLifecycleLogRepository(db),
    )


def _dto_to_dict(dto) -> dict:
    return asdict(dto)


@router.get("/visible-for-task")
def visible_for_task(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, _, _, _, _, access_control, _, _, agency, _ = _repos(db)
    uc = ListVisibleGroupsForTaskUseCase(repo, access_control, agency)
    result = uc.execute(current_user)
    return success(result)


@router.get("")
def list_groups(
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    region_code: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, _, _, _, _, access_control, _, _, agency, _ = _repos(db)
    uc = ListGroupsUseCase(repo, access_control, agency)
    result = uc.execute(current_user, keyword=keyword, status=status, region_code=region_code, page=page, page_size=page_size)
    return success(_dto_to_dict(result))


@router.post("")
def create_group(
    payload: GroupCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, member_repo, _, _, _, access_control, audit, _, agency, _ = _repos(db)
    uc = CreateGroupUseCase(repo, member_repo, access_control, audit, agency)
    result = uc.execute(payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.get("/{group_id}")
def get_group_detail(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, _, _, _, _, access_control, _, _, agency, _ = _repos(db)
    uc = GetGroupDetailUseCase(repo, access_control, agency)
    result = uc.execute(group_id, current_user)
    return success(result)


@router.put("/{group_id}")
def update_group(
    group_id: int,
    payload: GroupUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, _, _, _, _, access_control, audit, _, agency, _ = _repos(db)
    uc = UpdateGroupUseCase(repo, access_control, audit, agency)
    result = uc.execute(group_id, payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{group_id}/approve")
def approve_group(
    group_id: int,
    payload: GroupApprove,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, _, _, _, _, access_control, audit, _, agency, _ = _repos(db)
    uc = ApproveGroupUseCase(repo, access_control, audit, agency)
    result = uc.execute(group_id, payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{group_id}/reject")
def reject_group(
    group_id: int,
    payload: GroupReject,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, _, _, _, _, access_control, audit, _, agency, _ = _repos(db)
    uc = RejectGroupUseCase(repo, access_control, audit, agency)
    result = uc.execute(group_id, payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.get("/{group_id}/lifecycle-logs")
def lifecycle_logs(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, _, _, access_control, _, _, _, lifecycle_repo = _repos(db)
    access_control.check_group_access(current_user, group_id)
    logs = lifecycle_repo.list_logs(group_id)
    return success(logs)


@router.get("/{group_id}/members")
def list_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, member_repo, _, _, _, access_control, _, _, agency, _ = _repos(db)
    uc = ListMembersUseCase(member_repo, access_control, agency)
    result = uc.execute(group_id, current_user)
    return success([asdict(r) for r in result])


@router.post("/{group_id}/members")
def add_member(
    group_id: int,
    payload: AddGroupMember,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, member_repo, _, _, _, access_control, audit, _, agency, _ = _repos(db)
    uc = AddMemberUseCase(member_repo, access_control, audit, agency)
    result = uc.execute(group_id, payload.model_dump(exclude_unset=True), current_user, db=db, request=request)
    db.commit()
    return success(asdict(result))


@router.delete("/{group_id}/members/{agency_id}")
def remove_member(
    group_id: int,
    agency_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, member_repo, node_repo, _, _, access_control, audit, _, _, _ = _repos(db)
    uc = RemoveMemberUseCase(member_repo, node_repo, access_control, audit)
    result = uc.execute(group_id, agency_id, current_user, db=db, request=request)
    db.commit()
    return success(result)


@router.get("/{group_id}/users")
def list_users(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, _, _, access_control, _, user_query, _, _ = _repos(db)
    access_control.check_group_access(current_user, group_id)
    user_query.set_current_user(current_user)
    result = user_query.list_group_users(group_id)
    return success(result)


@router.post("/{group_id}/users")
def add_user(
    group_id: int,
    payload: AddGroupUser,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, _, _, access_control, _, user_query, _, _ = _repos(db)
    access_control.check_group_admin_access(current_user, group_id)
    result = user_query.add_group_user(group_id, payload.user_id, payload.role_code, current_user)
    db.commit()
    return success(result)


@router.put("/{group_id}/users/{user_id}/role")
def update_user_role(
    group_id: int,
    user_id: int,
    payload: UpdateGroupUserRole,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, _, _, access_control, _, user_query, _, _ = _repos(db)
    access_control.check_group_admin_access(current_user, group_id)
    result = user_query.update_group_user_role(group_id, user_id, payload.role_code, current_user)
    db.commit()
    return success(result)


@router.delete("/{group_id}/users/{user_id}")
def remove_user(
    group_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, _, _, access_control, _, user_query, _, _ = _repos(db)
    access_control.check_group_admin_access(current_user, group_id)
    result = user_query.remove_group_user(group_id, user_id, current_user)
    db.commit()
    return success(result)


@router.get("/{group_id}/nodes")
def list_nodes(
    group_id: int,
    node_type: str | None = Query(default=None),
    node_usage_role: str | None = Query(default=None),
    auth_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, node_repo, _, _, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_access(current_user, group_id)
    node_repo.set_current_user(current_user)
    result = node_repo.list_nodes(group_id, node_type=node_type, node_usage_role=node_usage_role, auth_status=auth_status)
    return success(result)


@router.get("/{group_id}/available-nodes")
def available_nodes(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, node_repo, _, _, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_access(current_user, group_id)
    node_repo.set_current_user(current_user)
    visible_ids = access_control.get_visible_agency_ids(current_user)
    result = node_repo.list_available_nodes(group_id, visible_agency_ids=visible_ids)
    return success(result)


@router.post("/{group_id}/nodes")
def add_node(
    group_id: int,
    payload: AddGroupNode,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.group_service import add_group_node as _add
    result = _add(db, group_id, payload.model_dump(exclude_unset=True), current_user, request)
    db.commit()
    return success(result)


@router.delete("/{group_id}/nodes/{node_id}")
def remove_node(
    group_id: int,
    node_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    from app.services.group_service import remove_group_node as _remove
    result = _remove(db, group_id, node_id, current_user, request)
    db.commit()
    return success(result)


@router.get("/{group_id}/datasets")
def list_datasets(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, ds_repo, _, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_access(current_user, group_id)
    result = ds_repo.list_datasets(group_id)
    return success(result)


@router.get("/{group_id}/available-datasets")
def available_datasets(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, ds_repo, _, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_access(current_user, group_id)
    visible_ids = access_control.get_visible_agency_ids(current_user)
    result = ds_repo.list_available_datasets(group_id, visible_agency_ids=visible_ids)
    return success(result)


@router.post("/{group_id}/datasets")
def add_dataset(
    group_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, ds_repo, _, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_admin_access(current_user, group_id)
    dataset_id = payload.get("dataset_id")
    existing = ds_repo.get_dataset_auth(group_id, dataset_id)
    if existing and existing.auth_status == "active":
        return success({"id": existing.id, "group_id": group_id, "dataset_id": dataset_id})
    if existing:
        existing.reactivate()
        existing.authorized_by = current_user.id
        ds_repo.save_dataset_auth(existing)
    else:
        from ..domain.models import GroupDatasetAuth
        auth = GroupDatasetAuth(group_id=group_id, dataset_id=dataset_id, auth_status="active", authorized_by=current_user.id)
        ds_repo.save_dataset_auth(auth)
    db.commit()
    return success({"group_id": group_id, "dataset_id": dataset_id})


@router.delete("/{group_id}/datasets/{dataset_id}")
def remove_dataset(
    group_id: int,
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, ds_repo, _, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_admin_access(current_user, group_id)
    ds_repo.remove_dataset_auth(group_id, dataset_id)
    db.commit()
    return success(message="撤销数据集授权成功")


@router.get("/{group_id}/templates")
def list_templates(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, _, tpl_repo, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_access(current_user, group_id)
    result = tpl_repo.list_templates(group_id)
    return success(result)


@router.get("/{group_id}/available-templates")
def available_templates(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, _, tpl_repo, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_access(current_user, group_id)
    visible_ids = access_control.get_visible_agency_ids(current_user)
    result = tpl_repo.list_available_templates(group_id, visible_agency_ids=visible_ids)
    return success(result)


@router.post("/{group_id}/templates")
def add_template(
    group_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, _, tpl_repo, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_admin_access(current_user, group_id)
    template_id = payload.get("template_id")
    existing = tpl_repo.get_template_auth(group_id, template_id)
    if existing and existing.auth_status == "active":
        return success({"id": existing.id, "group_id": group_id, "template_id": template_id})
    if existing:
        existing.reactivate()
        existing.authorized_by = current_user.id
        tpl_repo.save_template_auth(existing)
    else:
        from ..domain.models import GroupTemplateAuth
        auth = GroupTemplateAuth(group_id=group_id, template_id=template_id, auth_status="active", authorized_by=current_user.id)
        tpl_repo.save_template_auth(auth)
    db.commit()
    return success({"group_id": group_id, "template_id": template_id})


@router.delete("/{group_id}/templates/{template_id}")
def remove_template(
    group_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    _, _, _, _, tpl_repo, access_control, _, _, _, _ = _repos(db)
    access_control.check_group_admin_access(current_user, group_id)
    tpl_repo.remove_template_auth(group_id, template_id)
    db.commit()
    return success(message="撤销模板授权成功")


@router.post("/{group_id}/delete-request")
def request_delete(
    group_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, _, _, _, _, access_control, audit, _, agency, _ = _repos(db)
    uc = RequestDeleteGroupUseCase(repo, access_control, audit, agency)
    result = uc.execute(group_id, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{group_id}/delete-approve")
def approve_delete(
    group_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, _, _, _, _, access_control, audit, _, agency, _ = _repos(db)
    uc = ApproveDeleteGroupUseCase(repo, access_control, audit, agency)
    result = uc.execute(group_id, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))


@router.post("/{group_id}/delete-reject")
def reject_delete(
    group_id: int,
    payload: RejectDeleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    repo, _, _, _, _, access_control, audit, _, agency, _ = _repos(db)
    uc = RejectDeleteGroupUseCase(repo, access_control, audit, agency)
    result = uc.execute(group_id, payload.reason, current_user, db=db, request=request)
    db.commit()
    return success(_dto_to_dict(result))
