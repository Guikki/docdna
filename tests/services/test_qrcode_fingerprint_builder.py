from __future__ import annotations

from app.domain.fingerprints.qrcode_fingerprint import QRCodeFingerprint
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation
from app.services.qrcode_fingerprint_builder import QRCodeFingerprintBuilder


def test_should_build_qrcode_fingerprint() -> None:

    builder = QRCodeFingerprintBuilder()

    location = DocumentLocation(
        page_number=3,
        bounding_box=BoundingBox(
            x=120,
            y=80,
            width=180,
            height=180,
        ),
    )

    confidence = ConfidenceScore(0.99)

    fingerprint = builder.build(
        location=location,
        confidence=confidence,
        value="https://docdna.local/document/123",
        encoding="UTF-8",
        version=7,
        error_correction="M",
        image_hash="hash123",
        rotation=90.0,
    )

    assert isinstance(fingerprint, QRCodeFingerprint)

    assert fingerprint.location == location
    assert fingerprint.confidence == confidence

    assert fingerprint.value == "https://docdna.local/document/123"
    assert fingerprint.encoding == "UTF-8"
    assert fingerprint.version == 7
    assert fingerprint.error_correction == "M"
    assert fingerprint.image_hash == "hash123"
    assert fingerprint.rotation == 90.0


def test_should_build_qrcode_with_optional_fields_as_none() -> None:

    builder = QRCodeFingerprintBuilder()

    location = DocumentLocation(
        page_number=1,
        bounding_box=BoundingBox(
            x=0,
            y=0,
            width=100,
            height=100,
        ),
    )

    confidence = ConfidenceScore(0.95)

    fingerprint = builder.build(
        location=location,
        confidence=confidence,
        value="ABC123",
    )

    assert fingerprint.value == "ABC123"

    assert fingerprint.encoding is None
    assert fingerprint.version is None
    assert fingerprint.error_correction is None
    assert fingerprint.image_hash is None
    assert fingerprint.rotation == 0.0