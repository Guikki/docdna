from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PrintedNumericLine:
    line_index: int
    source: str
    raw_content: str
    normalized_content: str
    digit_count: int
    contextual_kind: str = "unclassified"
    contextual_metadata: dict[str, Any] = field(default_factory=dict)
