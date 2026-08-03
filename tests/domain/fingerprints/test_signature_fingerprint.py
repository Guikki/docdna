from __future__ import annotations

import pytest

from app.domain.fingerprints.signature_fingerprint import SignatureFingerprint
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation


@pytest.fixture
def location() -> DocumentLocation:
    return DocumentLocation(
        page_number=1,
        bounding_box=BoundingBox(
            x=50,
            y=700,
            width=220,
            height=60,
        ),
    )


@pytest.fixture
def confidence() -> ConfidenceScore:
    return ConfidenceScore(0.97)


def test_should_create_signature_fingerprint(
    location: DocumentLocation,
    confidence: ConfidenceScore,
):
    fingerprint = SignatureFingerprint(
        location=location,
        confidence=confidence,
        perceptual_hash="abc123",
        width=220,
        height=60,
        signer_name="João Silva",
    )

    assert fingerprint.location == location
    assert fingerprint.confidence == confidence
    assert fingerprint.perceptual_hash == "abc123"
    assert fingerprint.width == 220
    assert fingerprint.height == 60
    assert fingerprint.signer_name == "João Silva"


def test_should_create_signature_without_signer_name(
    location: DocumentLocation,
    confidence: ConfidenceScore,
):
    fingerprint = SignatureFingerprint(
        location=location,
        confidence=confidence,
        perceptual_hash="abc123",
        width=220,
        height=60,
    )

    assert fingerprint.signer_name is None