from app.domain.models.analysis_context import AnalysisContext
from app.domain.models.document import Document
from app.domain.readers.barcode_reader import BarcodeReader
from app.domain.readers.image_reader import ImageReader
from app.domain.readers.native_text_reader import NativeTextReader
from app.domain.readers.ocr_reader import OcrReader
from app.domain.readers.pdf_reader import PdfReader
from app.domain.readers.printed_numeric_line_reader import (
    PrintedNumericLineReader,
)
from app.domain.rules.numeric_line_validator import NumericLineValidator
from app.domain.services.numeric_line_visual_evidence_builder import (
    NumericLineVisualEvidenceBuilder,
)


class AnalysisContextBuilder:

    def build(self, document: Document) -> AnalysisContext:
        source = document.saved_path

        # Leitura estrutural e extração de dados brutos
        pdf_info = PdfReader().read(source)
        native_text = NativeTextReader().read(source)

        # Uma única execução do OCR gera texto e caixas posicionais
        ocr_result = OcrReader(language="por").read(source)

        ocr = ocr_result.document_ocr
        ocr_text_boxes = ocr_result.text_boxes

        images = ImageReader().read(source)
        barcodes = BarcodeReader().read(source)

        # Extração de possíveis linhas digitáveis
        printed_numeric_lines = PrintedNumericLineReader().read(
            native_text=native_text,
            ocr=ocr,
        )

        # Validação estrutural das sequências encontradas
        numeric_line_validator = NumericLineValidator()

        numeric_line_validations = [
            numeric_line_validator.validate(line)
            for line in printed_numeric_lines
        ]

        # Geração das evidências visuais usando
        # as coordenadas obtidas na mesma execução do OCR
        numeric_line_locations = (
            NumericLineVisualEvidenceBuilder().build(
                pdf_path=source,
                lines=printed_numeric_lines,
                boxes=ocr_text_boxes,
            )
        )

        return AnalysisContext(
            document_id=document.id,
            original_filename=document.original_filename,
            stored_filename=document.stored_filename,
            saved_path=document.saved_path,
            extension=document.extension,
            mime_type=document.mime_type,
            size_bytes=document.size_bytes,
            sha256=document.sha256,
            uploaded_at=document.uploaded_at,
            status=document.status,
            pdf_info=pdf_info,
            native_text=native_text,
            ocr=ocr,
            images=images,
            barcodes=barcodes,
            printed_numeric_lines=printed_numeric_lines,
            numeric_line_validations=numeric_line_validations,
            ocr_text_boxes=ocr_text_boxes,
            numeric_line_locations=numeric_line_locations,
        )