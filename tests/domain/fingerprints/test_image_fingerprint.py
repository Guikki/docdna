from __future__ import annotations

import pytest

from app.domain.fingerprints.image_fingerprint import ImageFingerprint
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
            height=80,
        ),
    )


@pytest.fixture
def confidence() -> ConfidenceScore:
    return ConfidenceScore(0.98)


def test_should_create_image_fingerprint(
    location: DocumentLocation,
    confidence: ConfidenceScore,
):
    fingerprint = ImageFingerprint(
        location=location,
        confidence=confidence,
        perceptual_hash="abc123",
        average_hash="avg123",
        difference_hash="diff123",
        image_hash="sha256",
        width=800,
        height=600,
        dpi=300,
        mime_type="image/png",
        description="Logo da concessionária",
    )

    assert fingerprint.location == location
    assert fingerprint.confidence == confidence
    assert fingerprint.perceptual_hash == "abc123"
    assert fingerprint.average_hash == "avg123"
    assert fingerprint.difference_hash == "diff123"
    assert fingerprint.image_hash == "sha256"
    assert fingerprint.width == 800
    assert fingerprint.height == 600
    assert fingerprint.dpi == 300
    assert fingerprint.mime_type == "image/png"
    assert fingerprint.description == "Logo da concessionária"


def test_should_raise_when_perceptual_hash_is_empty(
    location: DocumentLocation,
    confidence: ConfidenceScore,
):
    with pytest.raises(
        ValueError,
        match="perceptual_hash cannot be empty.",
    ):
        ImageFingerprint(
            location=location,
            confidence=confidence,
            perceptual_hash="",
            width=100,
            height=100,
        )


@pytest.mark.parametrize("width", [0, -1, -10])
def test_should_raise_when_width_is_not_greater_than_zero(
    location: DocumentLocation,
    confidence: ConfidenceScore,
    width: int,
):
    with pytest.raises(
        ValueError,
        match="width must be greater than zero.",
    ):
        ImageFingerprint(
            location=location,
            confidence=confidence,
            perceptual_hash="abc123",
            width=width,
            height=100,
        )


@pytest.mark.parametrize("height", [0, -1, -10])
def test_should_raise_when_height_is_not_greater_than_zero(
    location: DocumentLocation,
    confidence: ConfidenceScore,
    height: int,
):
    with pytest.raises(
        ValueError,
        match="height must be greater than zero.",
    ):
        ImageFingerprint(
            location=location,
            confidence=confidence,
            perceptual_hash="abc123",
            width=100,
            height=height,
        )