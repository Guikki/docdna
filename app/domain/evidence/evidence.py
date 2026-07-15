from dataclasses import dataclass
from enum import Enum


class EvidenceSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Evidence:
    code: str
    title: str
    description: str
    severity: EvidenceSeverity
    detector: str
    confidence: float