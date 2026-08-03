from datetime import date

from app.domain.models.detected_date import (
    DateSource,
    DetectedDate,
)
from app.domain.services.document_fingerprint_builder import (
    DocumentFingerprintBuilder,
)


def test_build_empty_fingerprint():

    builder = DocumentFingerprintBuilder()

    fingerprint = builder.build(
        document_id="doc-1",
    )

    assert fingerprint.document_id == "doc-1"
    assert fingerprint.is_empty


def test_build_complete_fingerprint():

    builder = DocumentFingerprintBuilder()

    detected = DetectedDate(
        value=date(2025, 1, 1),
        raw_content="01/01/2025",
        source=DateSource.OCR,
        document_id="doc-99",
        confidence=0.98,
    )

    fingerprint = builder.build(
        document_id="doc-99",
        file_name="conta.pdf",
        file_hash="hash",
        visual_hash="visual",
        text_hash="text",
        metadata_hash="metadata",
        barcode_values=("123",),
        qrcode_values=("QR",),
        detected_dates=(detected,),
        image_hashes=("img",),
        font_names=("Arial",),
        metadata_fields={"Author": "Adobe"},
        page_count=2,
        text_length=1800,
    )

    assert fingerprint.document_id == "doc-99"

    assert fingerprint.file_hash == "hash"

    assert fingerprint.visual_hash == "visual"

    assert fingerprint.text_hash == "text"

    assert fingerprint.metadata_hash == "metadata"

    assert fingerprint.page_count == 2

    assert fingerprint.text_length == 1800

    assert fingerprint.has_barcodes

    assert fingerprint.has_qrcodes

    assert fingerprint.has_dates

    assert fingerprint.has_metadata_information

    assert fingerprint.has_visual_information


def test_builder_returns_immutable_tuples():

    builder = DocumentFingerprintBuilder()

    fingerprint = builder.build(
        document_id="doc-1",
        barcode_values=["1", "2"],
        qrcode_values=["A"],
        image_hashes=["img"],
        font_names=["Arial"],
    )

    assert isinstance(fingerprint.barcode_values, tuple)

    assert isinstance(fingerprint.qrcode_values, tuple)

    assert isinstance(fingerprint.image_hashes, tuple)

    assert isinstance(fingerprint.font_names, tuple)