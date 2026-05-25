from datetime import datetime
from ..domain.models import Agency
from ..domain.ports import AgencyRepository, AgencyPermissionPort, AgencyAuditPort
from ..domain.exceptions import (
    AgencyNotFound, AgencyCodeDuplicate, ParentAgencyNotFound,
    SelfParentForbidden, DescendantParentForbidden, InvalidAgencyStatus,
)
from .dtos import AgencyDTO, AgencyTreeDTO, PaginatedAgenciesDTO, DeleteResultDTO


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _to_dto(agency: Agency, parent_name: str | None = None, summary: dict | None = None) -> AgencyDTO:
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
        created_at=_format_dt(agency.created_at),
        updated_at=_format_dt(agency.updated_at),
        summary=summary or {},
    )


class ListAgenciesUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort):
        self._repo = repo
        self._permission = permission

    def execute(self, current_user, **filters) -> PaginatedAgenciesDTO:
        manageable_ids = self._permission.get_manageable_agency_ids(current_user)
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

    def execute(self, current_user) -> list[dict]:
        manageable_ids = self._permission.get_manageable_agency_ids(current_user)
        return self._repo.get_agency_tree(manageable_ids=manageable_ids)


class GetAgencyDetailUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort):
        self._repo = repo
        self._permission = permission

    def execute(self, agency_id: int, current_user) -> AgencyDTO:
        self._permission.check_can_manage_agency(current_user, agency_id)
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

    def execute(self, payload: dict, current_user, db=None, request=None) -> AgencyDTO:
        agency_code = payload.get("agency_code")
        if self._repo.get_by_code(agency_code):
            raise AgencyCodeDuplicate()

        parent_agency_id = payload.get("parent_agency_id")
        if parent_agency_id:
            parent = self._repo.get_by_id(parent_agency_id)
            if not parent:
                raise ParentAgencyNotFound()

        self._permission.check_can_create_child_agency(current_user, parent_agency_id, payload.get("agency_level"))

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
        )
        agency = self._repo.save(agency)

        if db and self._audit:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="AGENCY_CREATE", resource_type="agency",
                resource_id=agency.id, agency_id=agency.id, request=request,
            )
            self._audit.anchor_resource_operation(
                db, resource_type="agency", resource_id=agency.id,
                operation_type="create", operator=current_user,
                agency_id=agency.id, before_data=None, after_data=agency,
            )

        return _to_dto(agency, self._repo.get_agency_name(agency.parent_agency_id), self._repo.get_summary(agency.id))


class UpdateAgencyUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort, audit: AgencyAuditPort):
        self._repo = repo
        self._permission = permission
        self._audit = audit

    def execute(self, agency_id: int, payload: dict, current_user, db=None, request=None) -> AgencyDTO:
        self._permission.check_can_manage_agency(current_user, agency_id)
        agency = self._repo.get_by_id(agency_id)
        if not agency:
            raise AgencyNotFound()

        new_parent_id = payload.get("parent_agency_id", agency.parent_agency_id)
        if new_parent_id == agency_id:
            raise SelfParentForbidden()

        descendant_ids = self._repo.get_agency_and_descendant_ids(agency_id)
        if new_parent_id in descendant_ids:
            raise DescendantParentForbidden()

        self._permission.check_can_create_child_agency(current_user, new_parent_id, payload.get("agency_level", agency.agency_level))

        before_data = agency
        agency.update_fields(**payload)
        agency = self._repo.save(agency)

        if db and self._audit:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="AGENCY_UPDATE", resource_type="agency",
                resource_id=agency.id, agency_id=agency.id, request=request,
            )
            self._audit.anchor_resource_operation(
                db, resource_type="agency", resource_id=agency.id,
                operation_type="update", operator=current_user,
                agency_id=agency.id, before_data=before_data, after_data=agency,
            )

        return _to_dto(agency, self._repo.get_agency_name(agency.parent_agency_id), self._repo.get_summary(agency.id))


class SetAgencyStatusUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort, audit: AgencyAuditPort):
        self._repo = repo
        self._permission = permission
        self._audit = audit

    def execute(self, agency_id: int, status: str, current_user, db=None, request=None) -> AgencyDTO:
        if status not in ("active", "disabled"):
            raise InvalidAgencyStatus()

        self._permission.check_can_manage_agency(current_user, agency_id)
        agency = self._repo.get_by_id(agency_id)
        if not agency:
            raise AgencyNotFound()

        before_data = agency
        agency.set_status(status)
        agency = self._repo.save(agency)

        if db and self._audit:
            operation_type = "AGENCY_ENABLE" if status == "active" else "AGENCY_DISABLE"
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type=operation_type, resource_type="agency",
                resource_id=agency.id, agency_id=agency.id, request=request,
            )
            self._audit.anchor_resource_operation(
                db, resource_type="agency", resource_id=agency.id,
                operation_type="enable" if status == "active" else "disable",
                operator=current_user, agency_id=agency.id,
                before_data=before_data, after_data=agency,
            )

        return _to_dto(agency, self._repo.get_agency_name(agency.parent_agency_id), self._repo.get_summary(agency.id))


class DeleteAgencyUseCase:
    def __init__(self, repo: AgencyRepository, permission: AgencyPermissionPort, audit: AgencyAuditPort):
        self._repo = repo
        self._permission = permission
        self._audit = audit

    def execute(self, agency_id: int, current_user, db=None, request=None) -> DeleteResultDTO:
        self._permission.check_can_manage_agency(current_user, agency_id)
        agency = self._repo.get_by_id(agency_id)
        if not agency:
            raise AgencyNotFound()
        return self._repo.delete(agency_id)
