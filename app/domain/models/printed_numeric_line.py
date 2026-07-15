from dataclasses import dataclass


@dataclass(frozen=True)
class PrintedNumericLine:
    line_index: int
    source: str
    raw_content: str
    normalized_content: str
    digit_count: int