from __future__ import annotations

from app.domain.fingerprints.signature_fingerprint import SignatureFingerprint
from app.domain.models.document_image import DocumentImage
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation
from app.services.signature_fingerprint_builder import SignatureFingerprintBuilder


def test_should_build_signature_fingerprint() -> None:

    builder = SignatureFingerprintBuilder()

    image = DocumentImage(
        image_index=1,
        page_number=1,
        xref=30,
        filename="signature.png",
        saved_path="output/signatures/signature.png",
        extension=".png",
        width=420,
        height=120,
        size_bytes=12000,
    )

    location = DocumentLocation(
        page_number=1,
        bounding_box=BoundingBox(
            x=100,
            y=500,
            width=420,
            height=120,
        ),
    )

    confidence = ConfidenceScore(0.97)

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
        description="Assinatura localizada",
        signer_name="João da Silva",
    )

    assert isinstance(fingerprint, SignatureFingerprint)

    assert fingerprint.width == 420
    assert fingerprint.height == 120
    assert fingerprint.signer_name == "João da Silva"
    assert fingerprint.perceptual_hash == "perceptual"
    assert fingerprint.average_hash == "average"
    assert fingerprint.difference_hash == "difference"
    assert fingerprint.image_hash == "sha256"


def test_should_build_signature_fingerprint_with_optional_fields_as_none() -> None:

    builder = SignatureFingerprintBuilder()

    image = DocumentImage(
        image_index=1,
        page_number=1,
        xref=1,
        filename="signature.png",
        saved_path="output/signature.png",
        extension=".png",
        width=200,
        height=60,
        size_bytes=1024,
    )

    location = DocumentLocation(
        page_number=1,
        bounding_box=BoundingBox(
            x=0,
            y=0,
            width=200,
            height=60,
        ),
    )

    confidence = ConfidenceScore(0.90)

    fingerprint = builder.build(
        image=image,
        location=location,
        confidence=confidence,
        perceptual_hash="hash",
    )

    assert fingerprint.signer_name is None
    assert fingerprint.average_hash is None
    assert fingerprint.difference_hash is None
    assert fingerprint.image_hash is None
    assert fingerprint.dpi is None
    assert fingerprint.mime_type is None
    assert fingerprint.description is None