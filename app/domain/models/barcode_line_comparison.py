from dataclasses import dataclass
from enum import Enum


class BarcodeLineComparisonStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class BarcodeLineComparison:
    line_index: int
    barcode_index: int | None
    line_type: str
    printed_numeric_line: str
    converted_barcode: str | None
    detected_barcode: str | None
    status: BarcodeLineComparisonStatus
    message: str