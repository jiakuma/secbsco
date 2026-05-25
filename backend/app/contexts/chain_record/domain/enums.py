from enum import Enum


class BizType(str, Enum):
    TASK = "task"
    TASK_RESULT = "task_result"
    AUDIT_LOG = "audit_log"


class ChainType(str, Enum):
    FISCO_BCOS = "fisco_bcos"


class ChainRecordStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class VerifyStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFY_SUCCESS = "verify_success"
    LOCAL_DATA_CHANGED = "local_data_changed"
    CHAIN_MISMATCH = "chain_mismatch"
    CHAIN_NOT_FOUND = "chain_not_found"
    QUERY_FAILED = "query_failed"
