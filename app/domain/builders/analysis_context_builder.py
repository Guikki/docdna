from app.domain.concealment.services.visual_concealment_analysis_service import (
    VisualConcealmentAnalysisService,
)
from app.domain.concealment.services.visual_concealment_evidence_builder import (
    VisualConcealmentEvidenceBuilder,
)
from app.domain.document.adapters.native_document_adapter import (
    NativeDocumentAdapter,
)
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
from app.domain.rules.numeric_line_validator import (
    NumericLineValidator,
)
from app.domain.services.numeric_line_visual_evidence_builder import (
    NumericLineVisualEvidenceBuilder,
)
from app.observability.performance_timer import (
    PerformanceTimer,
)
from app.processors.image_fingerprint_processor import (
    ImageFingerprintProcessor,
)
from app.processors.qrcode_fingerprint_processor import (
    QRCodeFingerprintProcessor,
)


class AnalysisContextBuilder:

    def __init__(
        self,
    ) -> None:
        self._performance_report: dict | None = None

    @property
    def performance_report(
        self,
    ) -> dict | None:
        return self._performance_report

    def build(
        self,
        document: Document,
    ) -> AnalysisContext:
        timer = PerformanceTimer()

        source = document.saved_path

        with timer.measure(
            "pdf_reader"
        ):
            pdf_info = PdfReader().read(
                source
            )

        with timer.measure(
            "native_text_reader"
        ):
            native_text = (
                NativeTextReader()
                .read(
                    source
                )
            )

        with timer.measure(
            "ocr"
        ):
            ocr_result = (
                OcrReader(
                    language="por",
                )
                .read(
                    source
                )
            )

        ocr = (
            ocr_result
            .document_ocr
        )

        ocr_text_boxes = (
            ocr_result
            .text_boxes
        )

        with timer.measure(
            "native_document_adapter"
        ):
            normalized_document = (
                NativeDocumentAdapter()
                .adapt(
                    source=source,
                )
            )

        with timer.measure(
            "visual_concealment_analysis"
        ):
            visual_concealment_analysis = (
                VisualConcealmentAnalysisService()
                .analyze(
                    normalized_document,
                    pdf_path=source,
                )
            )

        with timer.measure(
            "visual_concealment_evidence"
        ):
            visual_concealment_locations = (
                VisualConcealmentEvidenceBuilder()
                .build(
                    pdf_path=source,
                    findings=(
                        visual_concealment_analysis
                        .text_concealment_findings
                    ),
                )
            )

        with timer.measure(
            "image_reader"
        ):
            images = (
                ImageReader()
                .read(
                    source
                )
            )

        image_fingerprint_processor = (
            ImageFingerprintProcessor()
        )

        image_fingerprints = (
            image_fingerprint_processor
            .process(
                source
            )
        )

        with timer.measure(
            "barcode_reader"
        ):
            barcodes = (
                BarcodeReader()
                .read(
                    source
                )
            )

        with timer.measure(
            "qrcode_fingerprint"
        ):
            qrcode_fingerprints = (
                QRCodeFingerprintProcessor()
                .process(
                    barcodes
                )
            )

        with timer.measure(
            "printed_numeric_line_reader"
        ):
            printed_numeric_lines = (
                PrintedNumericLineReader()
                .read(
                    native_text=(
                        native_text
                    ),
                    ocr=ocr,
                )
            )

        numeric_line_validator = (
            NumericLineValidator()
        )

        with timer.measure(
            "numeric_line_validation"
        ):
            numeric_line_validations = [
                numeric_line_validator
                .validate(
                    line
                )
                for line
                in printed_numeric_lines
            ]

        with timer.measure(
            "numeric_line_visual_evidence"
        ):
            numeric_line_locations = (
                NumericLineVisualEvidenceBuilder()
                .build(
                    pdf_path=source,
                    lines=(
                        printed_numeric_lines
                    ),
                    boxes=(
                        ocr_text_boxes
                    ),
                )
            )

        analysis_context = AnalysisContext(
            document_id=(
                document.id
            ),
            original_filename=(
                document.original_filename
            ),
            stored_filename=(
                document.stored_filename
            ),
            saved_path=(
                document.saved_path
            ),
            extension=(
                document.extension
            ),
            mime_type=(
                document.mime_type
            ),
            size_bytes=(
                document.size_bytes
            ),
            sha256=(
                document.sha256
            ),
            uploaded_at=(
                document.uploaded_at
            ),
            status=(
                document.status
            ),
            pdf_info=(
                pdf_info
            ),
            native_text=(
                native_text
            ),
            ocr=ocr,
            images=images,
            image_fingerprints=(
                image_fingerprints
            ),
            qrcode_fingerprints=(
                qrcode_fingerprints
            ),
            barcodes=(
                barcodes
            ),
            printed_numeric_lines=(
                printed_numeric_lines
            ),
            numeric_line_validations=(
                numeric_line_validations
            ),
            ocr_text_boxes=(
                ocr_text_boxes
            ),
            numeric_line_locations=(
                numeric_line_locations
            ),
            normalized_document=(
                normalized_document
            ),
            visual_concealment_analysis=(
                visual_concealment_analysis
            ),
            visual_concealment_locations=(
                visual_concealment_locations
            ),
        )

        self._performance_report = (
            self._merge_performance_reports(
                primary_report=(
                    timer.to_dict()
                ),
                secondary_report=(
                    getattr(
                        image_fingerprint_processor,
                        "performance_report",
                        None,
                    )
                ),
            )
        )

        return analysis_context
    @staticmethod
    def _merge_performance_reports(
        *,
        primary_report: dict,
        secondary_report: dict | None,
    ) -> dict:
        total_seconds = float(
            primary_report.get(
                "total_seconds",
                0.0,
            )
            or 0.0
        )

        merged_stages: dict = {}

        primary_stages = (
            primary_report.get(
                "stages",
                {},
            )
        )

        if isinstance(
            primary_stages,
            dict,
        ):
            merged_stages.update(
                {
                    name: dict(data)
                    for name, data
                    in primary_stages.items()
                    if isinstance(
                        data,
                        dict,
                    )
                }
            )

        secondary_stages = (
            (
                secondary_report
                or {}
            ).get(
                "stages",
                {},
            )
        )

        if isinstance(
            secondary_stages,
            dict,
        ):
            for (
                stage_name,
                stage_data,
            ) in secondary_stages.items():
                if not isinstance(
                    stage_data,
                    dict,
                ):
                    continue

                existing = (
                    merged_stages.get(
                        stage_name
                    )
                )

                if existing is None:
                    merged_stages[
                        stage_name
                    ] = dict(
                        stage_data
                    )
                    continue

                existing_duration = float(
                    existing.get(
                        "duration_seconds",
                        0.0,
                    )
                    or 0.0
                )

                existing_calls = int(
                    existing.get(
                        "calls",
                        0,
                    )
                    or 0
                )

                merged_stages[
                    stage_name
                ] = {
                    "duration_seconds": (
                        existing_duration
                        + float(
                            stage_data.get(
                                "duration_seconds",
                                0.0,
                            )
                            or 0.0
                        )
                    ),
                    "calls": (
                        existing_calls
                        + int(
                            stage_data.get(
                                "calls",
                                0,
                            )
                            or 0
                        )
                    ),
                }

        for stage_data in (
            merged_stages.values()
        ):
            duration = float(
                stage_data.get(
                    "duration_seconds",
                    0.0,
                )
                or 0.0
            )

            calls = int(
                stage_data.get(
                    "calls",
                    0,
                )
                or 0
            )

            stage_data[
                "duration_seconds"
            ] = round(
                duration,
                6,
            )

            stage_data[
                "calls"
            ] = calls

            stage_data[
                "average_seconds"
            ] = round(
                (
                    duration / calls
                    if calls > 0
                    else 0.0
                ),
                6,
            )

            stage_data[
                "percentage_of_total"
            ] = round(
                (
                    duration
                    / total_seconds
                    * 100.0
                    if total_seconds > 0
                    else 0.0
                ),
                2,
            )

        return {
            "total_seconds": round(
                total_seconds,
                6,
            ),
            "stages": (
                merged_stages
            ),
        }
