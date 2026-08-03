from datetime import date

from app.domain.models.detected_date import (
    DateSource,
    DetectedDate,
)
from app.domain.models.document_fingerprint import (
    DocumentFingerprint,
)


def test_empty_fingerprint():
    fingerprint = DocumentFingerprint(
        document_id="doc-1"
    )

    assert fingerprint.is_empty
    assert not fingerprint.has_visual_information
    assert not fingerprint.has_text_information
    assert not fingerprint.has_metadata_information
    assert not fingerprint.has_dates


def test_visual_information():
    fingerprint = DocumentFingerprint(
        document_id="doc-1",
        visual_hash="abc123",
    )

    assert fingerprint.has_visual_information
    assert not fingerprint.is_empty


def test_text_information():
    fingerprint = DocumentFingerprint(
        document_id="doc-1",
        text_hash="hash",
        text_length=123,
    )

    assert fingerprint.has_text_information


def test_metadata_information():
    fingerprint = DocumentFingerprint(
        document_id="doc-1",
        metadata_hash="meta",
    )

    assert fingerprint.has_metadata_information


def test_barcodes():
    fingerprint = DocumentFingerprint(
        document_id="doc-1",
        barcode_values=("123456",),
    )

    assert fingerprint.has_barcodes


def test_qrcodes():
    fingerprint = DocumentFingerprint(
        document_id="doc-1",
        qrcode_values=("ABC",),
    )

    assert fingerprint.has_qrcodes


def test_detected_dates():
    detected = DetectedDate(
        value=date(2025, 1, 1),
        raw_content="01/01/2025",
        source=DateSource.OCR,
        document_id="doc-1",
        confidence=0.95,
    )

    fingerprint = DocumentFingerprint(
        document_id="doc-1",
        detected_dates=(detected,),
    )

    assert fingerprint.has_dates


def test_image_hashes():
    fingerprint = DocumentFingerprint(
        document_id="doc-1",
        image_hashes=("img1", "img2"),
    )

    assert fingerprint.has_visual_information


def test_metadata_fields():
    fingerprint = DocumentFingerprint(
        document_id="doc-1",
        metadata_fields={
            "Author": "Adobe"
        },
    )

    assert fingerprint.has_metadata_information


def test_complete_fingerprint():
    fingerprint = DocumentFingerprint(
        document_id="doc-1",
        file_name="conta.pdf",
        file_hash="hash",
        visual_hash="visual",
        text_hash="text",
        metadata_hash="metadata",
        barcode_values=("123",),
        qrcode_values=("abc",),
        image_hashes=("img",),
        font_names=("Arial",),
        metadata_fields={"Creator": "Word"},
        page_count=2,
        text_length=1500,
    )

    assert not fingerprint.is_empty
    assert fingerprint.page_count == 2
    assert fingerprint.text_length == 1500