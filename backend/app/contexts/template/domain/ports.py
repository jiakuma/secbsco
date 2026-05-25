from abc import ABC, abstractmethod
from .models import TemplateInfo


class TemplateRepository(ABC):
    @abstractmethod
    def get_by_id(self, template_id: int) -> TemplateInfo | None: ...

    @abstractmethod
    def get_by_code(self, template_code: str) -> TemplateInfo | None: ...

    @abstractmethod
    def list_templates(self, *, visible_agency_ids=None, keyword=None, agency_id=None, page=1, page_size=10) -> tuple[list[TemplateInfo], int]: ...

    @abstractmethod
    def save(self, template: TemplateInfo) -> TemplateInfo: ...

    @abstractmethod
    def delete(self, template_id: int) -> None: ...


class AccessControlPort(ABC):
    @abstractmethod
    def get_visible_agency_ids(self, current_user) -> list[int] | None: ...

    @abstractmethod
    def check_template_access(self, current_user, template: TemplateInfo, require_write: bool = False) -> None: ...

    @abstractmethod
    def require_admin(self, current_user) -> None: ...


class AgencyQueryPort(ABC):
    @abstractmethod
    def get_agency_name(self, agency_id: int | None) -> str | None: ...
