from io import BytesIO
from types import SimpleNamespace

import app.domain.use_cases.upload_document_use_case as module
from app.domain.use_cases.upload_document_use_case import (
    UploadDocumentUseCase,
)


class _FakeAnalysisContextBuilder:
    context = None

    def __init__(self) -> None:
        self.performance_report = {
            "total_seconds": 0.0,
            "stages": {
                "ocr": {
                    "duration_seconds": 0.0,
                    "calls": 1,
                    "average_seconds": 0.0,
                    "percentage_of_total": 0.0,
                }
            },
        }

    def build(
        self,
        document,
    ):
        return self.context


class _FakeBarcodePresenceDetector:
    def analyze(
        self,
        analysis_context,
    ) -> list:
        return []


class _FakeBarcodeNumericLineDetector:
    def compare(
        self,
        analysis_context,
    ) -> list:
        return []

    def analyze(
        self,
        analysis_context,
    ) -> list:
        return []


class _FakePromptInjectionAnalysisService:
    def analyze(
        self,
        *,
        native_text,
        ocr,
        normalized_document,
    ):
        return None


class _FakePromptInjectionVisualEvidenceBuilder:
    def build(
        self,
        **kwargs,
    ) -> list:
        raise AssertionError(
            "Visual builder should not run "
            "without prompt-injection evidences."
        )


def _configure_fakes(
    monkeypatch,
    tmp_path,
) -> None:
    context = SimpleNamespace(
        pdf_info=object(),
        native_text=object(),
        ocr=object(),
        images=[],
        image_fingerprints=[],
        qrcode_fingerprints=[],
        normalized_document=object(),
        visual_concealment_analysis=object(),
        visual_concealment_locations=[],
        barcodes=[],
        printed_numeric_lines=[],
        numeric_line_validations=[],
        numeric_line_locations=[],
        ocr_text_boxes=[],
    )

    _FakeAnalysisContextBuilder.context = context

    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(
            UPLOADS_DIR=tmp_path,
        ),
    )

    monkeypatch.setattr(
        module,
        "AnalysisContextBuilder",
        _FakeAnalysisContextBuilder,
    )

    monkeypatch.setattr(
        module,
        "BarcodePresenceDetector",
        _FakeBarcodePresenceDetector,
    )

    monkeypatch.setattr(
        module,
        "BarcodeNumericLineDetector",
        _FakeBarcodeNumericLineDetector,
    )

    monkeypatch.setattr(
        module,
        "PromptInjectionAnalysisService",
        _FakePromptInjectionAnalysisService,
    )

    monkeypatch.setattr(
        module,
        "PromptInjectionVisualEvidenceBuilder",
        _FakePromptInjectionVisualEvidenceBuilder,
    )


def test_execute_should_expose_performance_report(
    monkeypatch,
    tmp_path,
) -> None:
    _configure_fakes(
        monkeypatch,
        tmp_path,
    )

    upload = SimpleNamespace(
        filename="documento.pdf",
        content_type="application/pdf",
        file=BytesIO(
            b"%PDF-1.4\n%%EOF"
        ),
    )

    result = (
        UploadDocumentUseCase()
        .execute(
            upload
        )
    )

    performance = result[
        "performance"
    ]

    assert (
        performance[
            "total_seconds"
        ]
        >= 0.0
    )

    assert list(
        performance[
            "stages"
        ].keys()
    ) == [
        "validate_pdf",
        "prepare_upload_directory",
        "save_file",
        "sha256",
        "barcode_presence_detector",
        "barcode_numeric_line_compare",
        "barcode_numeric_line_evidence",
        "prompt_injection_analysis",
        "prompt_injection_visual_evidence",
        "ocr",
    ]


def test_should_recalculate_merged_stage_percentage() -> None:
    use_case = UploadDocumentUseCase()

    merged = use_case._merge_performance_reports(
        primary_report={
            "total_seconds": 2.0,
            "stages": {
                "save_file": {
                    "duration_seconds": 0.5,
                    "calls": 1,
                }
            },
        },
        secondary_report={
            "total_seconds": 1.0,
            "stages": {
                "ocr": {
                    "duration_seconds": 1.0,
                    "calls": 1,
                    "percentage_of_total": 100.0,
                }
            },
        },
    )

    assert (
        merged[
            "stages"
        ][
            "save_file"
        ][
            "percentage_of_total"
        ]
        == 25.0
    )

    assert (
        merged[
            "stages"
        ][
            "ocr"
        ][
            "percentage_of_total"
        ]
        == 50.0
    )
