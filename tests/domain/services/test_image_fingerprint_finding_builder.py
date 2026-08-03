from __future__ import annotations

import pytest

from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationSeverity,
)
from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)
from app.domain.models.image_fingerprint_pair import (
    ImageFingerprintPair,
)
from app.domain.services.image_fingerprint_finding_builder import (
    ImageFingerprintFindingBuilder,
)
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from app.domain.value_objects.document_location import (
    DocumentLocation,
)


def create_fingerprint(
    *,
    page_number: int,
    image_hash: str,
    perceptual_hash: str = "0000000000000000",
    average_hash: str | None = "0000000000000000",
    difference_hash: str | None = "0000000000000000",
    width: int = 640,
    height: int = 480,
) -> ImageFingerprint:
    return ImageFingerprint(
        location=DocumentLocation(
            page_number=page_number,
            bounding_box=BoundingBox(
                x=0.0,
                y=0.0,
                width=float(width),
                height=float(height),
            ),
        ),
        confidence=ConfidenceScore(1.0),
        perceptual_hash=perceptual_hash,
        average_hash=average_hash,
        difference_hash=difference_hash,
        image_hash=image_hash,
        width=width,
        height=height,
        mime_type="image/png",
    )


def create_pair(
    *,
    first_width: int = 640,
    first_height: int = 480,
    second_width: int = 640,
    second_height: int = 480,
) -> ImageFingerprintPair:
    return ImageFingerprintPair(
        first_document_id="document-1",
        second_document_id="document-2",
        first_image=create_fingerprint(
            page_number=1,
            image_hash="a" * 64,
            width=first_width,
            height=first_height,
        ),
        second_image=create_fingerprint(
            page_number=2,
            image_hash="b" * 64,
            width=second_width,
            height=second_height,
        ),
    )


def create_comparison(
    *,
    exact_image_match: bool = False,
    perceptual_similarity: float,
    same_dimensions: bool,
    width_difference: int = 0,
    height_difference: int = 0,
) -> ImageFingerprintComparison:
    perceptual_distance = round(
        100 * (1.0 - perceptual_similarity)
    )

    return ImageFingerprintComparison(
        exact_image_match=exact_image_match,
        perceptual_distance=perceptual_distance,
        perceptual_similarity=perceptual_similarity,
        average_distance=1,
        average_similarity=0.98,
        difference_distance=2,
        difference_similarity=0.96,
        same_dimensions=same_dimensions,
        width_difference=width_difference,
        height_difference=height_difference,
    )


def test_should_build_exact_image_match_finding() -> None:
    pair = create_pair()

    comparison = create_comparison(
        exact_image_match=True,
        perceptual_similarity=1.0,
        same_dimensions=True,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=pair,
        comparison=comparison,
        comparator="ImageFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "IMAGE_EXACT_MATCH"
    assert finding.severity is CrossValidationSeverity.INFO
    assert finding.confidence == 1.0

    assert finding.comparator == (
        "ImageFingerprintCrossComparator"
    )

    assert finding.document_ids == [
        "document-1",
        "document-2",
    ]


def test_exact_match_should_have_priority_over_similarity(
) -> None:
    comparison = create_comparison(
        exact_image_match=True,
        perceptual_similarity=0.10,
        same_dimensions=False,
        width_difference=100,
        height_difference=100,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=create_pair(),
        comparison=comparison,
        comparator="ImageFingerprintCrossComparator",
    )

    assert len(findings) == 1
    assert findings[0].code == "IMAGE_EXACT_MATCH"
    assert findings[0].confidence == 1.0


def test_should_build_strong_match_with_medium_severity_for_same_dimensions(
) -> None:
    comparison = create_comparison(
        perceptual_similarity=0.98,
        same_dimensions=True,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=create_pair(),
        comparison=comparison,
        comparator="ImageFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "IMAGE_STRONG_VISUAL_MATCH"

    assert (
        finding.severity
        is CrossValidationSeverity.MEDIUM
    )

    assert finding.confidence == 0.98


def test_should_build_strong_match_with_low_severity_for_different_dimensions(
) -> None:
    comparison = create_comparison(
        perceptual_similarity=0.99,
        same_dimensions=False,
        width_difference=160,
        height_difference=120,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=create_pair(
            second_width=800,
            second_height=600,
        ),
        comparison=comparison,
        comparator="ImageFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "IMAGE_STRONG_VISUAL_MATCH"
    assert finding.severity is CrossValidationSeverity.LOW
    assert finding.confidence == 0.99


@pytest.mark.parametrize(
    "similarity",
    [
        0.95,
        0.96,
        0.97,
        0.979999,
    ],
)
def test_should_build_moderate_visual_match_finding(
    similarity: float,
) -> None:
    comparison = create_comparison(
        perceptual_similarity=similarity,
        same_dimensions=True,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=create_pair(),
        comparison=comparison,
        comparator="ImageFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "IMAGE_VISUAL_MATCH"
    assert finding.severity is CrossValidationSeverity.LOW
    assert finding.confidence == similarity


@pytest.mark.parametrize(
    "similarity",
    [
        0.949999,
        0.90,
        0.50,
        0.0,
    ],
)
def test_should_not_build_finding_below_threshold(
    similarity: float,
) -> None:
    comparison = create_comparison(
        perceptual_similarity=similarity,
        same_dimensions=True,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=create_pair(),
        comparison=comparison,
        comparator="ImageFingerprintCrossComparator",
    )

    assert findings == []


def test_should_include_comparison_metadata() -> None:
    comparison = create_comparison(
        perceptual_similarity=0.98,
        same_dimensions=False,
        width_difference=160,
        height_difference=120,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=create_pair(
            second_width=800,
            second_height=600,
        ),
        comparison=comparison,
        comparator="ImageFingerprintCrossComparator",
    )

    metadata = findings[0].metadata

    assert metadata["classification"] == "strong"
    assert metadata["exact_image_match"] is False
    assert metadata["perceptual_similarity"] == 0.98
    assert metadata["average_similarity"] == 0.98
    assert metadata["difference_similarity"] == 0.96
    assert metadata["same_dimensions"] is False
    assert metadata["width_difference"] == 160
    assert metadata["height_difference"] == 120


def test_should_include_first_image_metadata() -> None:
    comparison = create_comparison(
        perceptual_similarity=0.98,
        same_dimensions=True,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=create_pair(),
        comparison=comparison,
        comparator="ImageFingerprintCrossComparator",
    )

    first_image = findings[0].metadata["first_image"]

    assert first_image["page_number"] == 1
    assert first_image["width"] == 640
    assert first_image["height"] == 480
    assert first_image["mime_type"] == "image/png"
    assert first_image["image_hash"] == "a" * 64


def test_should_include_second_image_metadata() -> None:
    comparison = create_comparison(
        perceptual_similarity=0.98,
        same_dimensions=True,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=create_pair(),
        comparison=comparison,
        comparator="ImageFingerprintCrossComparator",
    )

    second_image = findings[0].metadata["second_image"]

    assert second_image["page_number"] == 2
    assert second_image["width"] == 640
    assert second_image["height"] == 480
    assert second_image["mime_type"] == "image/png"
    assert second_image["image_hash"] == "b" * 64


def test_should_normalize_comparator_name() -> None:
    comparison = create_comparison(
        perceptual_similarity=0.98,
        same_dimensions=True,
    )

    findings = ImageFingerprintFindingBuilder().build(
        pair=create_pair(),
        comparison=comparison,
        comparator=(
            "  ImageFingerprintCrossComparator  "
        ),
    )

    assert findings[0].comparator == (
        "ImageFingerprintCrossComparator"
    )


@pytest.mark.parametrize(
    "comparator",
    [
        "",
        "   ",
    ],
)
def test_should_reject_empty_comparator_name(
    comparator: str,
) -> None:
    comparison = create_comparison(
        perceptual_similarity=0.98,
        same_dimensions=True,
    )

    with pytest.raises(
        ValueError,
        match="comparator cannot be empty",
    ):
        ImageFingerprintFindingBuilder().build(
            pair=create_pair(),
            comparison=comparison,
            comparator=comparator,
        )