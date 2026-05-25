from dataclasses import dataclass, field


@dataclass
class TemplateDTO:
    id: int | None = None
    template_code: str = ""
    template_name: str = ""
    agency_id: int | None = None
    agency_name: str | None = None
    scenario: str | None = None
    exec_mode: str | None = None
    output_type: str | None = None
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class PaginatedTemplatesDTO:
    total: int = 0
    page: int = 1
    page_size: int = 10
    items: list[TemplateDTO] = field(default_factory=list)
