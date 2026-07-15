from dataclasses import dataclass


@dataclass(frozen=True)
class OcrTextBox:
    page_number: int
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int