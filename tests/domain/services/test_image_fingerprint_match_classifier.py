from __future__ import annotations

import pytest

from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)
from app.domain.models.image_match_classification import (
    ImageMatchClassification,
)
from app.domain.services.image_fingerprint_match_classifier import (
    ImageFingerprintMatchClassifier,
)


def create_comparison(
    *,
    exact_image_match: bool = False,
    perceptual_similarity: float = 0.0,
    same_dimensions: bool = False,
) -> ImageFingerprintComparison:
    total_bits = 100

    perceptual_distance = round(
        total_bits * (1.0 - perceptual_similarity)
    )

    return ImageFingerprintComparison(
        exact_image_match=exact_image_match,
        perceptual_distance=perceptual_distance,
        perceptual_similarity=perceptual_similarity,
        average_distance=None,
        average_similarity=None,
        difference_distance=None,
        difference_similarity=None,
        same_dimensions=same_dimensions,
        width_difference=0 if same_dimensions else 10,
        height_difference=0 if same_dimensions else 10,
    )


def test_should_classify_exact_image_match() -> None:
    comparison = create_comparison(
        exact_image_match=True,
        perceptual_similarity=1.0,
        same_dimensions=True,
    )

    result = ImageFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is ImageMatchClassification.EXACT


def test_exact_match_should_have_priority_over_similarity(
) -> None:
    comparison = create_comparison(
        exact_image_match=True,
        perceptual_similarity=0.10,
    )

    result = ImageFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is ImageMatchClassification.EXACT


@pytest.mark.parametrize(
    "similarity",
    [
        1.0,
        0.999,
        0.99,
        0.98,
    ],
)
def test_should_classify_strong_visual_match(
    similarity: float,
) -> None:
    comparison = create_comparison(
        perceptual_similarity=similarity,
    )

    result = ImageFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is ImageMatchClassification.STRONG


@pytest.mark.parametrize(
    "similarity",
    [
        0.979999,
        0.97,
        0.96,
        0.95,
    ],
)
def test_should_classify_moderate_visual_match(
    similarity: float,
) -> None:
    comparison = create_comparison(
        perceptual_similarity=similarity,
    )

    result = ImageFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is ImageMatchClassification.MODERATE


@pytest.mark.parametrize(
    "similarity",
    [
        0.949999,
        0.90,
        0.50,
        0.0,
    ],
)
def test_should_classify_no_visual_match(
    similarity: float,
) -> None:
    comparison = create_comparison(
        perceptual_similarity=similarity,
    )

    result = ImageFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is ImageMatchClassification.NONE


def test_dimensions_should_not_change_classification() -> None:
    classifier = ImageFingerprintMatchClassifier()

    same_dimensions = create_comparison(
        perceptual_similarity=0.98,
        same_dimensions=True,
    )

    different_dimensions = create_comparison(
        perceptual_similarity=0.98,
        same_dimensions=False,
    )

    assert (
        classifier.classify(same_dimensions)
        is ImageMatchClassification.STRONG
    )

    assert (
        classifier.classify(different_dimensions)
        is ImageMatchClassification.STRONG
    )


def test_should_return_enum_instance() -> None:
    comparison = create_comparison(
        perceptual_similarity=0.95,
    )

    result = ImageFingerprintMatchClassifier().classify(
        comparison
    )

    assert isinstance(
        result,
        ImageMatchClassification,
    )
