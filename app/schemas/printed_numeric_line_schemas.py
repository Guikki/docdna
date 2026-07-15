from pydantic import BaseModel


class PrintedNumericLineResponse(BaseModel):
    line_index: int
    source: str
    raw_content: str
    normalized_content: str
    digit_count: int