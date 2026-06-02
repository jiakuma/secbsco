from dataclasses import dataclass
from typing import Any


@dataclass
class ComputationResult:
    task_data: dict
    parties_data: list[dict]
    result_data: dict
    message: str
    computation_type: str = ""
