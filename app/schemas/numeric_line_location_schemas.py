from pydantic import BaseModel


class NumericLineLocationResponse(BaseModel):
    line_index: int
    page_number: int | None
    matched_content: str | None

    left: int | None
    top: int | None
    width: int | None
    height: int | None

    confidence: float | None

    source_image_path: str | None
    annotated_image_path: str | None

    located: bool
    message: str