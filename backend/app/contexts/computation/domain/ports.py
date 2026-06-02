from abc import ABC, abstractmethod
from typing import Any


class ComputationPort(ABC):
    @abstractmethod
    def run(self, db, task, **kwargs) -> dict:
        ...
