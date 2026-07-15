from dataclasses import dataclass
from enum import Enum
from typing import Any


class EvidenceSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DocumentEvidence:
    code: str
    title: str
    description: str
    severity: EvidenceSeverity
    confidence: float
    source: str
    document_ids: list[str]
    metadata: dict[str, Any]