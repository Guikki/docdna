from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.document.models.document import (
    Document as NormalizedDocument,
)
from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.models.barcode import Barcode
from app.domain.models.document_image import DocumentImage
from app.domain.models.document_ocr import DocumentOcr
from app.domain.models.document_text import DocumentText
from app.domain.models.numeric_line_location import (
    NumericLineLocation,
)
from app.domain.models.numeric_line_validation import (
    NumericLineValidation,
)
from app.domain.models.ocr_text_box import OcrTextBox
from app.domain.models.pdf_info import PdfInfo
from app.domain.models.printed_numeric_line import (
    PrintedNumericLine,
)
from app.domain.shared.enums import DocumentStatus


@dataclass(frozen=True)
class AnalysisContext:
    document_id: UUID
    original_filename: str
    stored_filename: str
    saved_path: str
    extension: str
    mime_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime
    status: DocumentStatus

    pdf_info: PdfInfo
    native_text: DocumentText
    ocr: DocumentOcr
    images: list[DocumentImage]
    image_fingerprints: list[ImageFingerprint]
    barcodes: list[Barcode]
    printed_numeric_lines: list[PrintedNumericLine]
    numeric_line_validations: list[NumericLineValidation]
    ocr_text_boxes: list[OcrTextBox]
    numeric_line_locations: list[NumericLineLocation]

    normalized_document: NormalizedDocument