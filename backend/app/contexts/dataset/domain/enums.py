from enum import Enum


class DatasetStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class DataType(str, Enum):
    FILE = "file"
    DATABASE = "database"
    API = "api"
