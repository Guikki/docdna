from dataclasses import dataclass

from app.domain.models.document_ocr import DocumentOcr
from app.domain.models.ocr_text_box import OcrTextBox


@dataclass(frozen=True)
class OcrResult:
    document_ocr: DocumentOcr
    text_boxes: list[OcrTextBox]