from __future__ import annotations

from typing import Any

from app.domain.comparators.cross_validation_engine import (
    CrossValidationEngine,
)
from app.domain.comparators.image_fingerprint_cross_comparator import (
    ImageFingerprintCrossComparator,
)
from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationSeverity,
)
from app.domain.value_objects.bounding_box import (
    BoundingBox,
)
from app.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from app.domain.value_objects.document_location import (
    DocumentLocation,
)


def create_image_fingerprint(
    *,
    page_number: int,
    image_hash: str,
    perceptual_hash: str = "0123456789abcdef",
    average_hash: str = "fedcba9876543210",
    difference_hash: str = "0011223344556677",
    width: int = 800,
    height: int = 600,
) -> ImageFingerprint:
    """
    Cria um fingerprint de imagem real para os cenários
    de integração do domínio.
    """

    return ImageFingerprint(
        location=DocumentLocation(
            page_number=page_number,
            bounding_box=BoundingBox(
                x=10.0,
                y=20.0,
                width=float(width),
                height=float(height),
            ),
        ),
        confidence=ConfidenceScore(
            value=1.0,
        ),
        perceptual_hash=perceptual_hash,
        average_hash=average_hash,
        difference_hash=difference_hash,
        image_hash=image_hash,
        width=width,
        height=height,
        dpi=300,
        mime_type="image/png",
        description="Imagem utilizada no teste de integração.",
    )


def create_analysis(
    *,
    document_id: str,
    image_fingerprints: list[ImageFingerprint],
) -> dict[str, Any]:
    """
    Cria a representação de uma análise aceita pelo
    ImageFingerprintPairGenerator.
    """

    return {
        "id": document_id,
        "image_fingerprints": image_fingerprints,
    }


def test_should_detect_identical_image_between_two_documents(
) -> None:
    """
    Valida o fluxo completo da comparação cruzada de imagens:

    CrossValidationEngine
        -> ImageFingerprintCrossComparator
        -> ImageFingerprintPairGenerator
        -> ImageFingerprintComparator
        -> ImageFingerprintMatchClassifier
        -> ImageFingerprintFindingBuilder
        -> CrossValidationResult
    """

    shared_image_hash = (
        "a3f1c9e84b7d6250"
        "8d14fa97c6302be1"
        "ef4598ac736d012b"
        "954ce781a62f3d09"
    )

    first_image = create_image_fingerprint(
        page_number=1,
        image_hash=shared_image_hash,
    )

    second_image = create_image_fingerprint(
        page_number=3,
        image_hash=shared_image_hash,
    )

    analyses = [
        create_analysis(
            document_id="document-a",
            image_fingerprints=[
                first_image,
            ],
        ),
        create_analysis(
            document_id="document-b",
            image_fingerprints=[
                second_image,
            ],
        ),
    ]

    engine = CrossValidationEngine(
        comparators=[
            ImageFingerprintCrossComparator(),
        ],
    )

    result = engine.execute(
        analyses=analyses,
    )

    assert result.has_findings
    assert result.total_findings == 1
    assert len(result.findings) == 1

    finding = result.findings[0]

    assert finding.code == "IMAGE_EXACT_MATCH"
    assert finding.title == "Imagem idêntica localizada"

    assert (
        finding.severity
        is CrossValidationSeverity.INFO
    )

    assert finding.confidence == 1.0

    assert (
        finding.comparator
        == "ImageFingerprintCrossComparator"
    )

    assert finding.document_ids == [
        "document-a",
        "document-b",
    ]

    assert finding.metadata[
        "classification"
    ] == "exact"

    assert finding.metadata[
        "exact_image_match"
    ] is True

    assert finding.metadata[
        "perceptual_distance"
    ] == 0

    assert finding.metadata[
        "perceptual_similarity"
    ] == 1.0

    assert finding.metadata[
        "average_distance"
    ] == 0

    assert finding.metadata[
        "average_similarity"
    ] == 1.0

    assert finding.metadata[
        "difference_distance"
    ] == 0

    assert finding.metadata[
        "difference_similarity"
    ] == 1.0

    assert finding.metadata[
        "same_dimensions"
    ] is True

    assert finding.metadata[
        "width_difference"
    ] == 0

    assert finding.metadata[
        "height_difference"
    ] == 0

    assert finding.metadata[
        "first_image"
    ][
        "page_number"
    ] == 1

    assert finding.metadata[
        "second_image"
    ][
        "page_number"
    ] == 3

    assert finding.metadata[
        "first_image"
    ][
        "image_hash"
    ] == shared_image_hash

    assert finding.metadata[
        "second_image"
    ][
        "image_hash"
    ] == shared_image_hash