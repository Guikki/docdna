from dataclasses import dataclass
from enum import Enum
from typing import Any


class CrossValidationSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class CrossValidationFinding:
    code: str
    title: str
    description: str
    severity: CrossValidationSeverity
    confidence: float
    comparator: str
    document_ids: list[str]
    metadata: dict[str, Any]