from dataclasses import dataclass
from enum import Enum


class NumericLineType(str, Enum):
    BANK_SLIP = "bank_slip"
    COLLECTION = "collection"
    UNKNOWN = "unknown"


class NumericLineValidationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class NumericLineValidation:
    line_index: int
    normalized_content: str
    line_type: NumericLineType
    status: NumericLineValidationStatus
    digit_count: int
    validation_method: str | None
    valid_check_digits: int
    total_check_digits: int
    message: str