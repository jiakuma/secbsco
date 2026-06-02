# application/use_cases.py

from datetime import datetime
from typing import Optional
from ..domain.models import Agency
from ..domain.ports import AgencyRepository, AgencyPermissionPort, AgencyAuditPort
from ..domain.exceptions import (
    AgencyNotFound, AgencyCodeDuplicate, ParentAgencyNotFound,
    SelfParentForbidden, DescendantParentForbidden, InvalidAgencyStatus,
)
from ..domain.value_objects import UserContext, AuditMetadata
from .dtos import AgencyDTO, PaginatedAgenciesDTO, DeleteResultDTO


def _to_dto(agency: Agency, parent_name: Optional[str] = None, summary: Optional[dict] = None) -> AgencyDTO:
    return AgencyDTO(
        id=agency.id,
        agency_code=agency.agency_code,
        agency_name=agency.agency_name,
        agency_type=agency.agency_type,
        agency_level=agency.agency_level,
        parent_agency_id=agency.parent_agency_id,
        parent_agency_name=parent_name,
        region_code=agency.region_code,
        region_name=agency.region_name,
        contact_person=agency.contact_person,
        contact_phone=agency.contact_phone,
        status=agency.status,
        description=agency.description,
        created_at=agency.created_at,
        updated_at=agency.updated_at,
        summary=summary or {},
    )


class ListAgenciesUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort):
        self._repo = repo
        self._permission = permission

    def execute(self, user: UserContext, **filters) -> PaginatedAgenciesDTO:
        manageable_ids = self._permission.get_manageable_agency_ids(user)
        agencies, total = self._repo.list_agencies(manageable_ids=manageable_ids, **filters)
        items = []
        for a in agencies:
            parent_name = self._repo.get_agency_name(a.parent_agency_id)
            summary = self._repo.get_summary(a.id)
            items.append(_to_dto(a, parent_name, summary))
        return PaginatedAgenciesDTO(
            total=total,
            page=filters.get("page", 1),
            page_size=filters.get("page_size", 10),
            items=items,
        )


class GetAgencyTreeUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort):
        self._repo = repo
        self._permission = permission

    def execute(self, user: UserContext) -> list[dict]:
        manageable_ids = self._permission.get_manageable_agency_ids(user)
        return self._repo.get_agency_tree(manageable_ids=manageable_ids)


class GetAgencyDetailUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort):
        self._repo = repo
        self._permission = permission

    def execute(self, agency_id: int, user: UserContext) -> AgencyDTO:
        self._permission.check_can_manage_agency(user, agency_id)
        agency = self._repo.get_by_id(agency_id)
        if not agency:
            raise AgencyNotFound()
        parent_name = self._repo.get_agency_name(agency.parent_agency_id)
        summary = self._repo.get_summary(agency.id)
        return _to_dto(agency, parent_name, summary)


class CreateAgencyUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort, audit: AgencyAuditPort):
        self._repo = repo
        self._permission = permission
        self._audit = audit

    def execute(self, payload: dict, user: UserContext, now: datetime) -> AgencyDTO:
        agency_code = payload.get("agency_code")
        if self._repo.get_by_code(agency_code):
            raise AgencyCodeDuplicate()

        parent_agency_id = payload.get("parent_agency_id")
        if parent_agency_id:
            parent = self._repo.get_by_id(parent_agency_id)
            if not parent:
                raise ParentAgencyNotFound()

        self._permission.check_can_create_child_agency(user, parent_agency_id, payload.get("agency_level"))

        status = payload.get("status") or "active"
        if status not in ("active", "disabled"):
            raise InvalidAgencyStatus()

        agency = Agency(
            agency_code=agency_code,
            agency_name=payload.get("agency_name"),
            agency_type=payload.get("agency_type"),
            agency_level=payload.get("agency_level"),
            parent_agency_id=parent_agency_id,
            region_code=payload.get("region_code"),
            region_name=payload.get("region_name"),
            contact_person=payload.get("contact_person"),
            contact_phone=payload.get("contact_phone"),
            description=payload.get("description"),
            status=status,
            created_at=now,
            updated_at=now,
        )
        agency = self._repo.save(agency)

        # 审计
        metadata = AuditMetadata(
            operation_type="AGENCY_CREATE",
            resource_type="agency",
            resource_id=agency.id,
            agency_id=agency.id,
        )
        self._audit.write_operate_log(metadata, user)
        self._audit.anchor_resource_operation(
            resource_type="agency",
            resource_id=agency.id,
            operation_type="create",
            operator=user,
            agency_id=agency.id,
            before_data=None,
            after_data=agency,
        )

        return _to_dto(agency, self._repo.get_agency_name(agency.parent_agency_id), self._repo.get_summary(agency.id))


class UpdateAgencyUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort, audit: AgencyAuditPort):
        self._repo = repo
        self._permission = permission
        self._audit = audit

    def execute(self, agency_id: int, payload: dict, user: UserContext, now: datetime) -> AgencyDTO:
        self._permission.check_can_manage_agency(user, agency_id)
        agency = self._repo.get_by_id(agency_id)
        if not agency:
            raise AgencyNotFound()

        new_parent_id = payload.get("parent_agency_id", agency.parent_agency_id)
        if new_parent_id == agency_id:
            raise SelfParentForbidden()

        descendant_ids = self._repo.get_agency_and_descendant_ids(agency_id)
        if new_parent_id in descendant_ids:
            raise DescendantParentForbidden()

        self._permission.check_can_create_child_agency(user, new_parent_id, payload.get("agency_level", agency.agency_level))

        before_data = agency
        agency.update_fields(now, **payload)
        agency = self._repo.save(agency)

        metadata = AuditMetadata(
            operation_type="AGENCY_UPDATE",
            resource_type="agency",
            resource_id=agency.id,
            agency_id=agency.id,
        )
        self._audit.write_operate_log(metadata, user)
        self._audit.anchor_resource_operation(
            resource_type="agency",
            resource_id=agency.id,
            operation_type="update",
            operator=user,
            agency_id=agency.id,
            before_data=before_data,
            after_data=agency,
        )

        return _to_dto(agency, self._repo.get_agency_name(agency.parent_agency_id), self._repo.get_summary(agency.id))


class SetAgencyStatusUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort, audit: AgencyAuditPort):
        self._repo = repo
        self._permission = permission
        self._audit = audit

    def execute(self, agency_id: int, status: str, user: UserContext, now: datetime) -> AgencyDTO:
        if status not in ("active", "disabled"):
            raise InvalidAgencyStatus()

        self._permission.check_can_manage_agency(user, agency_id)
        agency = self._repo.get_by_id(agency_id)
        if not agency:
            raise AgencyNotFound()

        before_data = agency
        agency.set_status(status, now)
        agency = self._repo.save(agency)

        operation_type = "AGENCY_ENABLE" if status == "active" else "AGENCY_DISABLE"
        metadata = AuditMetadata(
            operation_type=operation_type,
            resource_type="agency",
            resource_id=agency.id,
            agency_id=agency.id,
        )
        self._audit.write_operate_log(metadata, user)
        self._audit.anchor_resource_operation(
            resource_type="agency",
            resource_id=agency.id,
            operation_type="enable" if status == "active" else "disable",
            operator=user,
            agency_id=agency.id,
            before_data=before_data,
            after_data=agency,
        )

        return _to_dto(agency, self._repo.get_agency_name(agency.parent_agency_id), self._repo.get_summary(agency.id))


class DeleteAgencyUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort, audit: AgencyAuditPort):
        self._repo = repo
        self._permission = permission
        self._audit = audit

    def execute(self, agency_id: int, user: UserContext) -> DeleteResultDTO:
        self._permission.check_can_manage_agency(user, agency_id)
        agency = self._repo.get_by_id(agency_id)
        if not agency:
            raise AgencyNotFound()
        return self._repo.delete(agency_id)