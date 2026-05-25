from enum import Enum


class TemplateStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class ExecMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
