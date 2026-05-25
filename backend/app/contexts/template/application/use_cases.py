from ..domain.models import TemplateInfo
from ..domain.ports import TemplateRepository, AccessControlPort, AgencyQueryPort
from ..domain.exceptions import TemplateNotFound, TemplateCodeAlreadyExists, TemplateProtected
from .dtos import TemplateDTO, PaginatedTemplatesDTO


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _to_dto(t: TemplateInfo, agency_name: str | None = None) -> TemplateDTO:
    return TemplateDTO(
        id=t.id, template_code=t.template_code, template_name=t.template_name,
        agency_id=t.agency_id, agency_name=agency_name,
        scenario=t.scenario, exec_mode=t.exec_mode, output_type=t.output_type,
        description=t.description,
        created_at=_format_dt(t.created_at), updated_at=_format_dt(t.updated_at),
    )


class ListTemplatesUseCase:
    def __init__(self, repo: TemplateRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, current_user, **filters) -> PaginatedTemplatesDTO:
        visible_ids = self._access_control.get_visible_agency_ids(current_user)
        agency_id = filters.get("agency_id")
        if agency_id and visible_ids is not None and agency_id not in visible_ids:
            return PaginatedTemplatesDTO(total=0, page=filters.get("page", 1), page_size=filters.get("page_size", 10))
        templates, total = self._repo.list_templates(visible_agency_ids=visible_ids, **filters)
        items = [_to_dto(t, self._agency.get_agency_name(t.agency_id)) for t in templates]
        return PaginatedTemplatesDTO(total=total, page=filters.get("page", 1), page_size=filters.get("page_size", 10), items=items)


class GetTemplateDetailUseCase:
    def __init__(self, repo: TemplateRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, template_id: int, current_user) -> TemplateDTO:
        t = self._repo.get_by_id(template_id)
        if not t:
            raise TemplateNotFound()
        self._access_control.check_template_access(current_user, t)
        return _to_dto(t, self._agency.get_agency_name(t.agency_id))


class CreateTemplateUseCase:
    def __init__(self, repo: TemplateRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, payload: dict, current_user) -> TemplateDTO:
        self._access_control.require_admin(current_user)
        agency_id = payload.get("agency_id") or current_user.agency_id
        visible_ids = self._access_control.get_visible_agency_ids(current_user)
        if agency_id and visible_ids is not None and agency_id not in visible_ids:
            from ..domain.exceptions import TemplateAccessDenied
            raise TemplateAccessDenied("无权在该机构下创建模板")
        if self._repo.get_by_code(payload.get("template_code")):
            raise TemplateCodeAlreadyExists()
        t = TemplateInfo(
            agency_id=agency_id,
            template_code=payload.get("template_code"), template_name=payload.get("template_name"),
            scenario=payload.get("scenario"), exec_mode=payload.get("exec_mode"),
            output_type=payload.get("output_type"), description=payload.get("description"),
            created_by=current_user.id,
        )
        t = self._repo.save(t)
        return _to_dto(t, self._agency.get_agency_name(t.agency_id))


class UpdateTemplateUseCase:
    def __init__(self, repo: TemplateRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, template_id: int, payload: dict, current_user) -> TemplateDTO:
        t = self._repo.get_by_id(template_id)
        if not t:
            raise TemplateNotFound()
        self._access_control.check_template_access(current_user, t, require_write=True)
        update_fields = ["template_name", "stat_type", "metrics_json", "params_schema_json",
                         "executor_config_json", "input_requirements_json", "output_view_type", "description"]
        for f in update_fields:
            if f in payload:
                setattr(t, f, payload[f])
        t = self._repo.save(t)
        return _to_dto(t, self._agency.get_agency_name(t.agency_id))


class DeleteTemplateUseCase:
    def __init__(self, repo: TemplateRepository, access_control: AccessControlPort):
        self._repo = repo
        self._access_control = access_control

    def execute(self, template_id: int, current_user, db=None) -> dict:
        t = self._repo.get_by_id(template_id)
        if not t:
            raise TemplateNotFound()
        self._access_control.check_template_access(current_user, t, require_write=True)
        if t.is_protected():
            raise TemplateProtected()
        self._repo.delete(template_id)
        return {"id": template_id}
