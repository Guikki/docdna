from __future__ import annotations

import pytest

from app.domain.fingerprints.barcode_fingerprint import BarcodeFingerprint
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
            width=120,
            height=60,
        ),
    )


@pytest.fixture
def confidence() -> ConfidenceScore:
    return ConfidenceScore(0.98)


def test_should_create_barcode_fingerprint(
    location: DocumentLocation,
    confidence: ConfidenceScore,
) -> None:
    fingerprint = BarcodeFingerprint(
        location=location,
        confidence=confidence,
        value="23793381286008200005332000012345678901234567",
        symbology="ITF",
        image_hash="abc123",
        rotation=90.0,
        raw_text="23793381286008200005332000012345678901234567",
    )

    assert fingerprint.location == location
    assert fingerprint.confidence == confidence

    assert (
        fingerprint.value
        == "23793381286008200005332000012345678901234567"
    )

    assert fingerprint.symbology == "ITF"
    assert fingerprint.image_hash == "abc123"
    assert fingerprint.rotation == 90.0

    assert (
        fingerprint.raw_text
        == "23793381286008200005332000012345678901234567"
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_should_raise_when_value_is_empty(
    value: str,
    location: DocumentLocation,
    confidence: ConfidenceScore,
) -> None:
    with pytest.raises(
        ValueError,
        match="Barcode value cannot be empty.",
    ):
        BarcodeFingerprint(
            location=location,
            confidence=confidence,
            value=value,
        )


def test_should_allow_optional_fields_to_be_none(
    location: DocumentLocation,
    confidence: ConfidenceScore,
) -> None:
    fingerprint = BarcodeFingerprint(
        location=location,
        confidence=confidence,
        value="1234567890",
    )

    assert fingerprint.symbology is None
    assert fingerprint.image_hash is None
    assert fingerprint.raw_text is None
    assert fingerprint.rotation == 0.0