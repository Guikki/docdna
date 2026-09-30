from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import app.domain.builders.analysis_context_builder as module
from app.domain.builders.analysis_context_builder import (
    AnalysisContextBuilder,
)
from app.domain.shared.enums import DocumentStatus


class _FakePdfReader:
    def read(self, source):
        return object()


class _FakeNativeTextReader:
    def read(self, source):
        return object()


class _FakeOcrReader:
    def __init__(self, *, language):
        self.language = language

    def read(self, source):
        return SimpleNamespace(
            document_ocr=object(),
            text_boxes=[],
        )


class _FakeNativeDocumentAdapter:
    def adapt(self, *, source):
        return object()


class _FakeVisualConcealmentAnalysisService:
    def analyze(
        self,
        normalized_document,
        *,
        pdf_path,
    ):
        return SimpleNamespace(
            text_concealment_findings=[],
        )


class _FakeVisualConcealmentEvidenceBuilder:
    def build(self, **kwargs):
        return []


class _FakeImageReader:
    def read(self, source):
        return []


class _FakeImageFingerprintProcessor:
    def __init__(self) -> None:
        self.performance_report = {
            "total_seconds": 0.0,
            "stages": {
                "image_fp_extraction": {
                    "duration_seconds": 0.0,
                    "calls": 1,
                },
                "image_hash_sha256": {
                    "duration_seconds": 0.0,
                    "calls": 1,
                },
                "image_hash_phash": {
                    "duration_seconds": 0.0,
                    "calls": 1,
                },
                "image_fp_build": {
                    "duration_seconds": 0.0,
                    "calls": 1,
                },
            },
        }

    def process(self, source):
        return []


class _FakeBarcodeReader:
    def read(self, source):
        return []


class _FakeQRCodeFingerprintProcessor:
    def process(self, barcodes):
        return []


class _FakePrintedNumericLineReader:
    def read(self, *, native_text, ocr):
        return []


class _FakeNumericLineValidator:
    def validate(self, line):
        return object()


class _FakeNumericLineVisualEvidenceBuilder:
    def build(self, **kwargs):
        return []


def test_should_report_analysis_context_pipeline_stages(
    monkeypatch,
) -> None:
    replacements = {
        "PdfReader": _FakePdfReader,
        "NativeTextReader": _FakeNativeTextReader,
        "OcrReader": _FakeOcrReader,
        "NativeDocumentAdapter": _FakeNativeDocumentAdapter,
        "VisualConcealmentAnalysisService": (
            _FakeVisualConcealmentAnalysisService
        ),
        "VisualConcealmentEvidenceBuilder": (
            _FakeVisualConcealmentEvidenceBuilder
        ),
        "ImageReader": _FakeImageReader,
        "ImageFingerprintProcessor": (
            _FakeImageFingerprintProcessor
        ),
        "BarcodeReader": _FakeBarcodeReader,
        "QRCodeFingerprintProcessor": (
            _FakeQRCodeFingerprintProcessor
        ),
        "PrintedNumericLineReader": (
            _FakePrintedNumericLineReader
        ),
        "NumericLineValidator": (
            _FakeNumericLineValidator
        ),
        "NumericLineVisualEvidenceBuilder": (
            _FakeNumericLineVisualEvidenceBuilder
        ),
    }

    for name, replacement in replacements.items():
        monkeypatch.setattr(
            module,
            name,
            replacement,
        )

    document = SimpleNamespace(
        id=uuid4(),
        original_filename="documento.pdf",
        stored_filename="documento-id.pdf",
        saved_path="documento-id.pdf",
        extension=".pdf",
        mime_type="application/pdf",
        size_bytes=123,
        sha256="a" * 64,
        uploaded_at=datetime.now(),
        status=DocumentStatus.RECEIVED,
    )

    builder = AnalysisContextBuilder()

    builder.build(
        document
    )

    report = builder.performance_report

    assert report is not None

    stages = report["stages"]

    assert list(stages.keys()) == [
        "pdf_reader",
        "native_text_reader",
        "ocr",
        "native_document_adapter",
        "visual_concealment_analysis",
        "visual_concealment_evidence",
        "image_reader",
        "barcode_reader",
        "qrcode_fingerprint",
        "printed_numeric_line_reader",
        "numeric_line_validation",
        "numeric_line_visual_evidence",
        "image_fp_extraction",
        "image_hash_sha256",
        "image_hash_phash",
        "image_fp_build",
    ]

    assert all(
        stage["calls"] == 1
        for stage
        in stages.values()
    )

    assert (
        "image_fingerprint"
        not in stages
    )
