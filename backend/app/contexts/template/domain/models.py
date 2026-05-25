from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TemplateInfo:
    id: int | None = None
    agency_id: int | None = None
    template_code: str = ""
    template_name: str = ""
    scenario: str | None = None
    exec_mode: str | None = None
    output_type: str | None = None
    stat_type: str | None = None
    metrics_json: dict | None = None
    params_schema_json: dict | None = None
    executor_config_json: dict | None = None
    input_requirements_json: dict | None = None
    output_view_type: str | None = None
    template_hash: str | None = None
    status: str = "enabled"
    version: int = 1
    created_by: int | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    PROTECTED_CODES = frozenset([
        "T1_JOINT_CASE_STAT_TEMPLATE",
        "T2_SPATIOTEMPORAL_TEMPLATE",
        "T3_KEY_POPULATION_RISK_TEMPLATE",
    ])

    def is_protected(self) -> bool:
        return self.template_code in self.PROTECTED_CODES
