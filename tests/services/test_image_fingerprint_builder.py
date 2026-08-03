from __future__ import annotations

from app.domain.fingerprints.image_fingerprint import ImageFingerprint
from app.domain.models.document_image import DocumentImage
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation
from app.services.image_fingerprint_builder import ImageFingerprintBuilder


def test_should_build_image_fingerprint() -> None:
    builder = ImageFingerprintBuilder()

    image = DocumentImage(
        image_index=1,
        page_number=2,
        xref=15,
        filename="document_page_2_image_1.png",
        saved_path="output/images/document_page_2_image_1.png",
        extension=".png",
        width=320,
        height=180,
        size_bytes=20480,
    )

    location = DocumentLocation(
        page_number=2,
        bounding_box=BoundingBox(
            x=10,
            y=20,
            width=320,
            height=180,
        ),
    )

    confidence = ConfidenceScore(0.98)

    fingerprint = builder.build(
        image=image,
        location=location,
        confidence=confidence,
        perceptual_hash="perceptual-hash",
        average_hash="average-hash",
        difference_hash="difference-hash",
        image_hash="sha256-hash",
        dpi=300,
        mime_type="image/png",
        description="Imagem extraída do documento",
    )

    assert isinstance(fingerprint, ImageFingerprint)

    assert fingerprint.location == location
    assert fingerprint.confidence == confidence

    assert fingerprint.perceptual_hash == "perceptual-hash"
    assert fingerprint.average_hash == "average-hash"
    assert fingerprint.difference_hash == "difference-hash"
    assert fingerprint.image_hash == "sha256-hash"

    assert fingerprint.width == image.width
    assert fingerprint.height == image.height

    assert fingerprint.dpi == 300
    assert fingerprint.mime_type == "image/png"
    assert fingerprint.description == "Imagem extraída do documento"


def test_should_build_image_fingerprint_with_optional_fields_as_none() -> None:
    builder = ImageFingerprintBuilder()

    image = DocumentImage(
        image_index=1,
        page_number=1,
        xref=10,
        filename="image.jpeg",
        saved_path="output/images/image.jpeg",
        extension=".jpeg",
        width=200,
        height=100,
        size_bytes=10240,
    )

    location = DocumentLocation(
        page_number=1,
        bounding_box=BoundingBox(
            x=0,
            y=0,
            width=200,
            height=100,
        ),
    )

    confidence = ConfidenceScore(0.90)

    fingerprint = builder.build(
        image=image,
        location=location,
        confidence=confidence,
        perceptual_hash="required-perceptual-hash",
    )

    assert fingerprint.perceptual_hash == "required-perceptual-hash"

    assert fingerprint.average_hash is None
    assert fingerprint.difference_hash is None
    assert fingerprint.image_hash is None
    assert fingerprint.dpi is None
    assert fingerprint.mime_type is None
    assert fingerprint.description is None

    assert fingerprint.width == 200
    assert fingerprint.height == 100