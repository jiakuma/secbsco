from enum import Enum


class OperationType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RUN = "run"
    ANCHOR = "anchor"
    APPROVE = "approve"
    JOIN = "join"


class ObjectType(str, Enum):
    TASK = "task"
    TASK_RESULT = "task_result"
    GROUP = "group"
    AGENCY = "agency"
    NODE = "node"
    DATASET = "dataset"
    TEMPLATE = "template"
    CHAIN_RECORD = "chain_record"
    AUDIT_LOG = "audit_log"
