from __future__ import annotations

import pytest

from app.domain.models.logo_fingerprint_comparison import (
    LogoFingerprintComparison,
)
from app.domain.models.logo_match_classification import (
    LogoMatchClassification,
)
from app.domain.services.logo_fingerprint_match_classifier import (
    LogoFingerprintMatchClassifier,
)


def create_comparison(
    *,
    exact_image_match: bool = False,
    perceptual_similarity: float = 0.0,
    same_company_name: bool | None = None,
) -> LogoFingerprintComparison:
    return LogoFingerprintComparison(
        exact_image_match=exact_image_match,
        perceptual_distance=0,
        perceptual_similarity=perceptual_similarity,
        average_distance=None,
        average_similarity=None,
        difference_distance=None,
        difference_similarity=None,
        same_dimensions=True,
        width_difference=0,
        height_difference=0,
        same_company_name=same_company_name,
    )


def test_should_classify_exact_image_match_as_exact(
) -> None:
    comparison = create_comparison(
        exact_image_match=True,
        perceptual_similarity=0.10,
    )

    result = LogoFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is LogoMatchClassification.EXACT


def test_should_prioritize_exact_match_over_visual_similarity(
) -> None:
    comparison = create_comparison(
        exact_image_match=True,
        perceptual_similarity=1.0,
    )

    result = LogoFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is LogoMatchClassification.EXACT


@pytest.mark.parametrize(
    "similarity",
    [
        0.98,
        0.99,
        1.0,
    ],
)
def test_should_classify_strong_visual_similarity(
    similarity: float,
) -> None:
    comparison = create_comparison(
        perceptual_similarity=similarity,
    )

    result = LogoFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is LogoMatchClassification.STRONG


@pytest.mark.parametrize(
    "similarity",
    [
        0.95,
        0.96,
        0.979999,
    ],
)
def test_should_classify_moderate_visual_similarity(
    similarity: float,
) -> None:
    comparison = create_comparison(
        perceptual_similarity=similarity,
    )

    result = LogoFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is LogoMatchClassification.MODERATE


@pytest.mark.parametrize(
    "similarity",
    [
        0.0,
        0.50,
        0.949999,
    ],
)
def test_should_classify_low_visual_similarity_as_none(
    similarity: float,
) -> None:
    comparison = create_comparison(
        perceptual_similarity=similarity,
    )

    result = LogoFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is LogoMatchClassification.NONE


def test_should_preserve_visual_classification_when_company_matches(
) -> None:
    comparison = create_comparison(
        perceptual_similarity=0.99,
        same_company_name=True,
    )

    result = LogoFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is LogoMatchClassification.STRONG


def test_should_preserve_visual_classification_when_company_differs(
) -> None:
    comparison = create_comparison(
        perceptual_similarity=0.99,
        same_company_name=False,
    )

    result = LogoFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is LogoMatchClassification.STRONG


def test_should_preserve_visual_classification_without_company_comparison(
) -> None:
    comparison = create_comparison(
        perceptual_similarity=0.99,
        same_company_name=None,
    )

    result = LogoFingerprintMatchClassifier().classify(
        comparison
    )

    assert result is LogoMatchClassification.STRONG