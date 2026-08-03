from datetime import datetime
from uuid import uuid4

from fastapi import UploadFile

from app.config.settings import settings
from app.domain.models.document import Document
from app.domain.shared.enums import DocumentStatus
from app.utils.hash_utils import calculate_sha256
from app.domain.builders.analysis_context_builder import AnalysisContextBuilder
from app.domain.detectors.barcode_presence_detector import BarcodePresenceDetector
from app.domain.detectors.barcode_numeric_line_detector import (
    BarcodeNumericLineDetector,
)


class UploadDocumentUseCase:
    def execute(self, file: UploadFile) -> dict:
        self._validate_pdf(file)

        upload_dir = settings.UPLOADS_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)

        document_id = uuid4()
        extension = ".pdf"
        stored_filename = f"{document_id}{extension}"
        saved_path = upload_dir / stored_filename

        with saved_path.open("wb") as buffer:
            buffer.write(file.file.read())

        document = Document(
            id=document_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            saved_path=str(saved_path),
            extension=extension,
            mime_type=file.content_type or "application/pdf",
            size_bytes=saved_path.stat().st_size,
            sha256=calculate_sha256(saved_path),
            uploaded_at=datetime.now(),
            status=DocumentStatus.RECEIVED,
        )

        analysis_context = AnalysisContextBuilder().build(document)
        barcode_presence_detector = BarcodePresenceDetector()
        barcode_numeric_line_detector = BarcodeNumericLineDetector()

        barcode_presence_evidences = barcode_presence_detector.analyze(
            analysis_context
        )

        barcode_line_comparisons = barcode_numeric_line_detector.compare(
            analysis_context
        )

        barcode_comparison_evidences = barcode_numeric_line_detector.analyze(
            analysis_context
        )

        evidences = [
            *barcode_presence_evidences,
            *barcode_comparison_evidences,
        ]


        return {
            "id": document.id,
            "original_filename": document.original_filename,
            "stored_filename": document.stored_filename,
            "saved_path": document.saved_path,
            "extension": document.extension,
            "mime_type": document.mime_type,
            "size_bytes": document.size_bytes,
            "sha256": document.sha256,
            "uploaded_at": document.uploaded_at,
            "status": document.status.value,
            "pdf_info": analysis_context.pdf_info,
            "native_text": analysis_context.native_text,
            "ocr": analysis_context.ocr,
            "images": analysis_context.images,
            "image_fingerprints": (
                analysis_context.image_fingerprints
            ),
            "normalized_document": (
                analysis_context.normalized_document
            ),
            "barcodes": analysis_context.barcodes,
            "printed_numeric_lines": analysis_context.printed_numeric_lines,
            "numeric_line_validations": analysis_context.numeric_line_validations,
            "numeric_line_locations": analysis_context.numeric_line_locations,
            "barcode_line_comparisons": barcode_line_comparisons,
            "evidences": evidences,
            "message": "Documento recebido, identificado e lido com sucesso.",
        }

    def _validate_pdf(self, file: UploadFile) -> None:
        if not file.filename.lower().endswith(".pdf"):
            raise ValueError("Apenas arquivos PDF são permitidos.")