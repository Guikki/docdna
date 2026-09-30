from datetime import datetime
from uuid import uuid4

from fastapi import UploadFile

from app.config.settings import settings
from app.domain.builders.analysis_context_builder import (
    AnalysisContextBuilder,
)
from app.domain.detectors.barcode_numeric_line_detector import (
    BarcodeNumericLineDetector,
)
from app.domain.detectors.barcode_presence_detector import (
    BarcodePresenceDetector,
)
from app.domain.models.document import Document
from app.domain.prompt_injection.services.prompt_injection_analysis_service import (
    PromptInjectionAnalysisService,
)
from app.domain.prompt_injection.services.prompt_injection_visual_evidence_builder import (
    PromptInjectionVisualEvidenceBuilder,
)
from app.domain.shared.enums import DocumentStatus
from app.observability.performance_timer import (
    PerformanceTimer,
)
from app.utils.hash_utils import calculate_sha256


class UploadDocumentUseCase:
    def execute(
        self,
        file: UploadFile,
    ) -> dict:
        timer = PerformanceTimer()

        with timer.measure(
            "validate_pdf"
        ):
            self._validate_pdf(
                file
            )

        upload_dir = (
            settings.UPLOADS_DIR
        )

        with timer.measure(
            "prepare_upload_directory"
        ):
            upload_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

        document_id = uuid4()

        extension = ".pdf"

        stored_filename = (
            f"{document_id}{extension}"
        )

        saved_path = (
            upload_dir
            / stored_filename
        )

        with timer.measure(
            "save_file"
        ):
            with saved_path.open(
                "wb"
            ) as buffer:
                buffer.write(
                    file.file.read()
                )

        with timer.measure(
            "sha256"
        ):
            sha256 = calculate_sha256(
                saved_path
            )

        document = Document(
            id=document_id,
            original_filename=(
                file.filename
            ),
            stored_filename=(
                stored_filename
            ),
            saved_path=str(
                saved_path
            ),
            extension=extension,
            mime_type=(
                file.content_type
                or "application/pdf"
            ),
            size_bytes=(
                saved_path
                .stat()
                .st_size
            ),
            sha256=sha256,
            uploaded_at=datetime.now(),
            status=(
                DocumentStatus.RECEIVED
            ),
        )

        analysis_context_builder = (
            AnalysisContextBuilder()
        )

        analysis_context = (
            analysis_context_builder
            .build(
                document
            )
        )

        barcode_presence_detector = (
            BarcodePresenceDetector()
        )

        barcode_numeric_line_detector = (
            BarcodeNumericLineDetector()
        )

        prompt_injection_service = (
            PromptInjectionAnalysisService()
        )

        prompt_injection_visual_builder = (
            PromptInjectionVisualEvidenceBuilder()
        )

        with timer.measure(
            "barcode_presence_detector"
        ):
            barcode_presence_evidences = (
                barcode_presence_detector
                .analyze(
                    analysis_context
                )
            )

        with timer.measure(
            "barcode_numeric_line_compare"
        ):
            barcode_line_comparisons = (
                barcode_numeric_line_detector
                .compare(
                    analysis_context
                )
            )

        with timer.measure(
            "barcode_numeric_line_evidence"
        ):
            barcode_comparison_evidences = (
                barcode_numeric_line_detector
                .analyze(
                    analysis_context
                )
            )

        with timer.measure(
            "prompt_injection_analysis"
        ):
            prompt_injection_assessment = (
                prompt_injection_service
                .analyze(
                    native_text=(
                        analysis_context
                        .native_text
                    ),
                    ocr=(
                        analysis_context
                        .ocr
                    ),
                    normalized_document=(
                        analysis_context
                        .normalized_document
                    ),
                )
            )

        with timer.measure(
            "prompt_injection_visual_evidence"
        ):
            prompt_injection_locations = (
                self._build_prompt_injection_locations(
                    pdf_path=str(
                        saved_path
                    ),
                    analysis_context=(
                        analysis_context
                    ),
                    assessment=(
                        prompt_injection_assessment
                    ),
                    visual_builder=(
                        prompt_injection_visual_builder
                    ),
                )
            )

        evidences = [
            *barcode_presence_evidences,
            *barcode_comparison_evidences,
        ]

        performance = self._merge_performance_reports(
            primary_report=(
                timer.to_dict()
            ),
            secondary_report=(
                getattr(
                    analysis_context_builder,
                    "performance_report",
                    None,
                )
            ),
        )

        return {
            "id": (
                document.id
            ),

            "original_filename": (
                document.original_filename
            ),

            "stored_filename": (
                document.stored_filename
            ),

            "saved_path": (
                document.saved_path
            ),

            "extension": (
                document.extension
            ),

            "mime_type": (
                document.mime_type
            ),

            "size_bytes": (
                document.size_bytes
            ),

            "sha256": (
                document.sha256
            ),

            "uploaded_at": (
                document.uploaded_at
            ),

            "status": (
                document.status.value
            ),

            "pdf_info": (
                analysis_context.pdf_info
            ),

            "native_text": (
                analysis_context.native_text
            ),

            "ocr": (
                analysis_context.ocr
            ),

            "images": (
                analysis_context.images
            ),

            "image_fingerprints": (
                analysis_context
                .image_fingerprints
            ),

            "qrcode_fingerprints": (
                analysis_context
                .qrcode_fingerprints
            ),

            "normalized_document": (
                analysis_context
                .normalized_document
            ),

            "visual_concealment_analysis": (
                analysis_context
                .visual_concealment_analysis
            ),

            "visual_concealment_locations": (
                analysis_context
                .visual_concealment_locations
            ),

            "barcodes": (
                analysis_context.barcodes
            ),

            "printed_numeric_lines": (
                analysis_context
                .printed_numeric_lines
            ),

            "numeric_line_validations": (
                analysis_context
                .numeric_line_validations
            ),

            "numeric_line_locations": (
                analysis_context
                .numeric_line_locations
            ),

            "barcode_line_comparisons": (
                barcode_line_comparisons
            ),

            "prompt_injection_assessment": (
                prompt_injection_assessment
            ),

            "prompt_injection_locations": (
                prompt_injection_locations
            ),

            "evidences": (
                evidences
            ),

            "performance": (
                performance
            ),

            "message": (
                "Documento recebido, "
                "identificado e lido "
                "com sucesso."
            ),
        }

    def _merge_performance_reports(
        self,
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

        merged_stages: dict = {
            name: dict(stage)
            for name, stage
            in primary_report.get(
                "stages",
                {},
            ).items()
        }

        if isinstance(
            secondary_report,
            dict,
        ):
            secondary_stages = (
                secondary_report.get(
                    "stages",
                    {},
                )
            )

            if isinstance(
                secondary_stages,
                dict,
            ):
                for (
                    name,
                    stage,
                ) in secondary_stages.items():
                    if not isinstance(
                        stage,
                        dict,
                    ):
                        continue

                    duration_seconds = float(
                        stage.get(
                            "duration_seconds",
                            0.0,
                        )
                        or 0.0
                    )

                    calls = int(
                        stage.get(
                            "calls",
                            0,
                        )
                        or 0
                    )

                    existing = (
                        merged_stages.get(
                            name
                        )
                    )

                    if isinstance(
                        existing,
                        dict,
                    ):
                        duration_seconds += float(
                            existing.get(
                                "duration_seconds",
                                0.0,
                            )
                            or 0.0
                        )

                        calls += int(
                            existing.get(
                                "calls",
                                0,
                            )
                            or 0
                        )

                    merged_stages[
                        name
                    ] = {
                        "duration_seconds": (
                            duration_seconds
                        ),
                        "calls": calls,
                    }

        normalized_stages = {}

        for (
            name,
            stage,
        ) in merged_stages.items():
            duration_seconds = float(
                stage.get(
                    "duration_seconds",
                    0.0,
                )
                or 0.0
            )

            calls = int(
                stage.get(
                    "calls",
                    0,
                )
                or 0
            )

            average_seconds = (
                duration_seconds / calls
                if calls > 0
                else 0.0
            )

            percentage_of_total = (
                duration_seconds
                / total_seconds
                * 100.0
                if total_seconds > 0
                else 0.0
            )

            normalized_stages[
                name
            ] = {
                "duration_seconds": round(
                    duration_seconds,
                    6,
                ),
                "calls": calls,
                "average_seconds": round(
                    average_seconds,
                    6,
                ),
                "percentage_of_total": round(
                    percentage_of_total,
                    2,
                ),
            }

        return {
            "total_seconds": round(
                total_seconds,
                6,
            ),
            "stages": normalized_stages,
        }

    def _build_prompt_injection_locations(
        self,
        *,
        pdf_path: str,
        analysis_context,
        assessment,
        visual_builder: (
            PromptInjectionVisualEvidenceBuilder
        ),
    ) -> list:
        """
        Produz localização visual das evidências de
        Prompt Injection utilizando estratégia native-first.

        O documento normalizado fornece os TextSpan nativos,
        com página, bounding box e metadados tipográficos.
        As caixas OCR permanecem disponíveis como fallback
        quando a localização nativa não for possível.

        Caso não existam evidências, retorna uma coleção
        vazia. Se não houver texto nativo nem caixas OCR,
        também não há material suficiente para localização.
        """

        if assessment is None:
            return []

        assessment_evidences = getattr(
            assessment,
            "evidences",
            None,
        )

        if not assessment_evidences:
            return []

        text_boxes = getattr(
            analysis_context,
            "ocr_text_boxes",
            None,
        )

        normalized_document = getattr(
            analysis_context,
            "normalized_document",
            None,
        )

        if text_boxes is None:
            text_boxes = []

        if not isinstance(
            text_boxes,
            list,
        ):
            return []

        if (
            normalized_document is None
            and not text_boxes
        ):
            return []

        return (
            visual_builder.build(
                pdf_path=pdf_path,
                evidences=list(
                    assessment_evidences
                ),
                boxes=text_boxes,
                normalized_document=(
                    normalized_document
                ),
            )
        )

    def _validate_pdf(
        self,
        file: UploadFile,
    ) -> None:
        filename = (
            file.filename
            or ""
        )

        if not filename.lower().endswith(
            ".pdf"
        ):
            raise ValueError(
                "Apenas arquivos PDF "
                "são permitidos."
            )
