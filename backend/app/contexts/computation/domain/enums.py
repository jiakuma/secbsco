from enum import Enum


class ComputationType(str, Enum):
    SECRETFLOW_STAT = "secretflow_statistic"
    SECRETFLOW_FL = "secretflow_federated_learning"
    BIO_TASK_RUNTIME = "bio_task_runtime"


class TaskExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
