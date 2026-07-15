from abc import ABC, abstractmethod
from typing import Any

from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
)


class BaseComparator(ABC):

    @abstractmethod
    def compare(
        self,
        analyses: list[dict[str, Any]],
    ) -> list[CrossValidationFinding]:
        raise NotImplementedError