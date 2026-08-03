from __future__ import annotations

import pytest

from app.domain.models.document_evidence import (
    EvidenceSeverity,
)
from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)
from app.domain.services.image_fingerprint_evidence_builder import (
    ImageFingerprintEvidenceBuilder,
)


def create_comparison(
    *,
    exact_image_match: bool = False,
    perceptual_distance: int = 4,
    perceptual_similarity: float = 0.9375,
    average_distance: int | None = 2,
    average_similarity: float | None = 0.96875,
    difference_distance: int | None = 3,
    difference_similarity: float | None = 0.953125,
    same_dimensions: bool = True,
    width_difference: int = 0,
    height_difference: int = 0,
) -> ImageFingerprintComparison:
    return ImageFingerprintComparison(
        exact_image_match=exact_image_match,
        perceptual_distance=perceptual_distance,
        perceptual_similarity=perceptual_similarity,
        average_distance=average_distance,
        average_similarity=average_similarity,
        difference_distance=difference_distance,
        difference_similarity=difference_similarity,
        same_dimensions=same_dimensions,
        width_difference=width_difference,
        height_difference=height_difference,
    )


def test_should_build_exact_image_match_evidence() -> None:
    comparison = create_comparison(
        exact_image_match=True,
        perceptual_distance=0,
        perceptual_similarity=1.0,
    )

    builder = ImageFingerprintEvidenceBuilder()

    result = builder.build(
        comparison=comparison,
        first_document_id="document-1",
        second_document_id="document-2",
        first_image_reference="page-1-image-1",
        second_image_reference="page-3-image-2",
    )

    assert len(result) == 1

    evidence = result[0]

    assert evidence.code == "IMAGE_EXACT_MATCH"
    assert evidence.severity == EvidenceSeverity.INFO
    assert evidence.confidence == 1.0

    assert evidence.document_ids == [
        "document-1",
        "document-2",
    ]

    assert (
        evidence.metadata["exact_image_match"]
        is True
    )

    assert (
        evidence.metadata["first_image_reference"]
        == "page-1-image-1"
    )

    assert (
        evidence.metadata["second_image_reference"]
        == "page-3-image-2"
    )


def test_should_build_strong_visual_match_evidence() -> None:
    comparison = create_comparison(
        perceptual_distance=1,
        perceptual_similarity=0.984375,
        same_dimensions=True,
    )

    result = ImageFingerprintEvidenceBuilder().build(
        comparison=comparison,
        first_document_id="document-1",
        second_document_id="document-2",
    )

    assert len(result) == 1

    evidence = result[0]

    assert evidence.code == "IMAGE_STRONG_VISUAL_MATCH"
    assert evidence.severity == EvidenceSeverity.MEDIUM
    assert evidence.confidence == pytest.approx(
        0.984375,
    )


def test_should_use_low_severity_when_strong_match_has_different_dimensions(
) -> None:
    comparison = create_comparison(
        perceptual_distance=1,
        perceptual_similarity=0.984375,
        same_dimensions=False,
        width_difference=20,
        height_difference=10,
    )

    result = ImageFingerprintEvidenceBuilder().build(
        comparison=comparison,
        first_document_id="document-1",
        second_document_id="document-2",
    )

    assert len(result) == 1
    assert result[0].severity == EvidenceSeverity.LOW


def test_should_build_moderate_visual_match_evidence() -> None:
    comparison = create_comparison(
        perceptual_distance=3,
        perceptual_similarity=0.953125,
    )

    result = ImageFingerprintEvidenceBuilder().build(
        comparison=comparison,
        first_document_id="document-1",
        second_document_id="document-2",
    )

    assert len(result) == 1

    evidence = result[0]

    assert evidence.code == "IMAGE_VISUAL_MATCH"
    assert evidence.severity == EvidenceSeverity.LOW
    assert evidence.confidence == pytest.approx(
        0.953125,
    )


def test_should_not_build_evidence_below_similarity_threshold() -> None:
    comparison = create_comparison(
        perceptual_distance=4,
        perceptual_similarity=0.9375,
    )

    result = ImageFingerprintEvidenceBuilder().build(
        comparison=comparison,
        first_document_id="document-1",
        second_document_id="document-2",
    )

    assert result == []


def test_exact_match_should_take_priority_over_visual_match() -> None:
    comparison = create_comparison(
        exact_image_match=True,
        perceptual_distance=0,
        perceptual_similarity=1.0,
    )

    result = ImageFingerprintEvidenceBuilder().build(
        comparison=comparison,
        first_document_id="document-1",
        second_document_id="document-2",
    )

    assert len(result) == 1
    assert result[0].code == "IMAGE_EXACT_MATCH"


def test_should_preserve_all_comparison_metadata() -> None:
    comparison = create_comparison(
        exact_image_match=False,
        perceptual_distance=1,
        perceptual_similarity=0.984375,
        average_distance=2,
        average_similarity=0.96875,
        difference_distance=3,
        difference_similarity=0.953125,
        same_dimensions=False,
        width_difference=100,
        height_difference=50,
    )

    result = ImageFingerprintEvidenceBuilder().build(
        comparison=comparison,
        first_document_id="document-1",
        second_document_id="document-2",
    )

    metadata = result[0].metadata

    assert metadata["perceptual_distance"] == 1
    assert metadata["perceptual_similarity"] == 0.984375
    assert metadata["average_distance"] == 2
    assert metadata["average_similarity"] == 0.96875
    assert metadata["difference_distance"] == 3
    assert metadata["difference_similarity"] == 0.953125
    assert metadata["same_dimensions"] is False
    assert metadata["width_difference"] == 100
    assert metadata["height_difference"] == 50


@pytest.mark.parametrize(
    "first_document_id,second_document_id,error_message",
    [
        (
            "",
            "document-2",
            "first_document_id cannot be empty",
        ),
        (
            "   ",
            "document-2",
            "first_document_id cannot be empty",
        ),
        (
            "document-1",
            "",
            "second_document_id cannot be empty",
        ),
        (
            "document-1",
            "   ",
            "second_document_id cannot be empty",
        ),
    ],
)
def test_should_reject_empty_document_ids(
    first_document_id: str,
    second_document_id: str,
    error_message: str,
) -> None:
    comparison = create_comparison(
        perceptual_distance=1,
        perceptual_similarity=0.984375,
    )

    with pytest.raises(
        ValueError,
        match=error_message,
    ):
        ImageFingerprintEvidenceBuilder().build(
            comparison=comparison,
            first_document_id=first_document_id,
            second_document_id=second_document_id,
        )


def test_should_normalize_document_ids() -> None:
    comparison = create_comparison(
        perceptual_distance=1,
        perceptual_similarity=0.984375,
    )

    result = ImageFingerprintEvidenceBuilder().build(
        comparison=comparison,
        first_document_id=" document-1 ",
        second_document_id=" document-2 ",
    )

    assert result[0].document_ids == [
        "document-1",
        "document-2",
    ]