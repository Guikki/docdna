from pydantic import BaseModel


class NumericLineValidationResponse(BaseModel):
    line_index: int
    normalized_content: str
    line_type: str
    status: str
    digit_count: int
    validation_method: str | None
    valid_check_digits: int
    total_check_digits: int
    message: str