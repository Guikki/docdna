from __future__ import annotations

import pytest

from app.domain.fingerprints.qrcode_fingerprint import QRCodeFingerprint
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation


@pytest.fixture
def location() -> DocumentLocation:
    return DocumentLocation(
        page_number=1,
        bounding_box=BoundingBox(
            x=10,
            y=20,
            width=100,
            height=100,
        ),
    )


@pytest.fixture
def confidence() -> ConfidenceScore:
    return ConfidenceScore(0.98)


def test_should_create_qrcode_fingerprint(
    location: DocumentLocation,
    confidence: ConfidenceScore,
):
    fingerprint = QRCodeFingerprint(
        location=location,
        confidence=confidence,
        value="https://docdna.local",
        encoding="UTF-8",
        version=5,
        error_correction="M",
        image_hash="abc123",
        rotation=90.0,
    )

    assert fingerprint.location == location
    assert fingerprint.confidence == confidence
    assert fingerprint.value == "https://docdna.local"
    assert fingerprint.encoding == "UTF-8"
    assert fingerprint.version == 5
    assert fingerprint.error_correction == "M"
    assert fingerprint.image_hash == "abc123"
    assert fingerprint.rotation == 90.0


def test_should_raise_when_value_is_empty(
    location: DocumentLocation,
    confidence: ConfidenceScore,
):
    with pytest.raises(
        ValueError,
        match="QR Code value cannot be empty.",
    ):
        QRCodeFingerprint(
            location=location,
            confidence=confidence,
            value="",
        )