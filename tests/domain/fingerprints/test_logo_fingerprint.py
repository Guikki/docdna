from __future__ import annotations

import pytest

from app.domain.fingerprints.logo_fingerprint import LogoFingerprint
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
            height=80,
        ),
    )


@pytest.fixture
def confidence() -> ConfidenceScore:
    return ConfidenceScore(0.99)


def test_should_create_logo_fingerprint(
    location: DocumentLocation,
    confidence: ConfidenceScore,
):
    fingerprint = LogoFingerprint(
        location=location,
        confidence=confidence,
        perceptual_hash="abc123",
        width=120,
        height=80,
        company_name="Pessoa & Pessoa",
    )

    assert fingerprint.location == location
    assert fingerprint.confidence == confidence
    assert fingerprint.perceptual_hash == "abc123"
    assert fingerprint.width == 120
    assert fingerprint.height == 80
    assert fingerprint.company_name == "Pessoa & Pessoa"


def test_should_create_logo_without_company_name(
    location: DocumentLocation,
    confidence: ConfidenceScore,
):
    fingerprint = LogoFingerprint(
        location=location,
        confidence=confidence,
        perceptual_hash="abc123",
        width=120,
        height=80,
    )

    assert fingerprint.company_name is None