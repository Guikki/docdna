from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.pdf_schemas import PdfInfoResponse
from app.schemas.text_schemas import DocumentTextResponse
from app.schemas.image_schemas import DocumentImageResponse
from app.schemas.ocr_schemas import DocumentOcrResponse
from app.schemas.barcode_schemas import BarcodeResponse
from app.schemas.evidence_schemas import EvidenceResponse
from app.schemas.printed_numeric_line_schemas import PrintedNumericLineResponse
from app.schemas.numeric_line_validation_schemas import (
    NumericLineValidationResponse,
)
from app.schemas.barcode_line_comparison_schemas import (
    BarcodeLineComparisonResponse,
)

from app.schemas.numeric_line_location_schemas import (
    NumericLineLocationResponse,
)



class UploadDocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    stored_filename: str
    saved_path: str
    extension: str
    mime_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime
    status: str
    pdf_info: PdfInfoResponse
    native_text: DocumentTextResponse
    ocr: DocumentOcrResponse
    images: list[DocumentImageResponse]
    barcodes: list[BarcodeResponse]
    printed_numeric_lines: list[PrintedNumericLineResponse]
    numeric_line_validations: list[NumericLineValidationResponse]
    barcode_line_comparisons: list[BarcodeLineComparisonResponse]
    numeric_line_locations: list[NumericLineLocationResponse]
    evidences: list[EvidenceResponse]
    message: str


