from pydantic import BaseModel, Field


class PrintedNumericLineResponse(BaseModel):
    line_index: int
    source: str
    raw_content: str
    normalized_content: str
    digit_count: int
    contextual_kind: str = "unclassified"
    contextual_metadata: dict = Field(default_factory=dict)
