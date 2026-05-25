from enum import Enum


class TaskStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class TaskType(str, Enum):
    STAT = "stat"
    FL_TRAIN = "fl_train"


class PartyRole(str, Enum):
    LEAD = "lead"
    PARTICIPANT = "participant"
    DATA_PROVIDER = "data_provider"
    COMPUTE_PROVIDER = "compute_provider"


class AnchorStatus(str, Enum):
    NONE = "none"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
