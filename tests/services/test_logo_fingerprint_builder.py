from __future__ import annotations

from app.domain.fingerprints.logo_fingerprint import LogoFingerprint
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation
from app.domain.models.document_image import DocumentImage
from app.services.logo_fingerprint_builder import LogoFingerprintBuilder


def test_should_build_logo_fingerprint() -> None:

    builder = LogoFingerprintBuilder()

    image = DocumentImage(
        image_index=1,
        page_number=1,
        xref=100,
        filename="logo.png",
        saved_path="output/images/logo.png",
        extension=".png",
        width=256,
        height=128,
        size_bytes=4096,
    )

    location = DocumentLocation(
        page_number=1,
        bounding_box=BoundingBox(
            x=50,
            y=40,
            width=256,
            height=128,
        ),
    )

    confidence = ConfidenceScore(0.99)

    fingerprint = builder.build(
        image=image,
        location=location,
        confidence=confidence,
        perceptual_hash="perceptual",
        average_hash="average",
        difference_hash="difference",
        image_hash="sha256",
        dpi=300,
        mime_type="image/png",
        description="Logo institucional",
        company_name="Pessoa e Pessoa",
    )

    assert isinstance(fingerprint, LogoFingerprint)

    assert fingerprint.width == 256
    assert fingerprint.height == 128
    assert fingerprint.company_name == "Pessoa e Pessoa"
    assert fingerprint.perceptual_hash == "perceptual"
    assert fingerprint.average_hash == "average"
    assert fingerprint.difference_hash == "difference"
    assert fingerprint.image_hash == "sha256"


def test_should_build_logo_fingerprint_with_optional_fields_as_none() -> None:

    builder = LogoFingerprintBuilder()

    image = DocumentImage(
        image_index=1,
        page_number=1,
        xref=1,
        filename="logo.png",
        saved_path="output/logo.png",
        extension=".png",
        width=100,
        height=80,
        size_bytes=1024,
    )

    location = DocumentLocation(
        page_number=1,
        bounding_box=BoundingBox(
            x=0,
            y=0,
            width=100,
            height=80,
        ),
    )

    confidence = ConfidenceScore(0.90)

    fingerprint = builder.build(
        image=image,
        location=location,
        confidence=confidence,
        perceptual_hash="hash",
    )

    assert fingerprint.company_name is None
    assert fingerprint.average_hash is None
    assert fingerprint.difference_hash is None
    assert fingerprint.image_hash is None
    assert fingerprint.dpi is None
    assert fingerprint.mime_type is None
    assert fingerprint.description is None