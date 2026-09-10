from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import app.domain.use_cases.upload_document_use_case as module
from app.domain.use_cases.upload_document_use_case import (
    UploadDocumentUseCase,
)


class _FakeAnalysisContextBuilder:
    context = None

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


def test_should_expose_qrcode_fingerprints_in_analysis_result(
    monkeypatch,
    tmp_path,
) -> None:
    qrcode_fingerprints = [
        object(),
        object(),
    ]

    context = SimpleNamespace(
        pdf_info=object(),
        native_text=object(),
        ocr=object(),
        images=[],
        image_fingerprints=[],
        qrcode_fingerprints=(
            qrcode_fingerprints
        ),
        normalized_document=object(),
        visual_concealment_analysis=object(),
        visual_concealment_locations=[],
        barcodes=[],
        printed_numeric_lines=[],
        numeric_line_validations=[],
        numeric_line_locations=[],
        ocr_text_boxes=[],
    )

    _FakeAnalysisContextBuilder.context = (
        context
    )

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

    assert (
        result["qrcode_fingerprints"]
        is qrcode_fingerprints
    )
