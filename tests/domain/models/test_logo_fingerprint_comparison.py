from __future__ import annotations

import pytest

from app.domain.models.logo_fingerprint_comparison import (
    LogoFingerprintComparison,
)


def create_comparison(
    *,
    same_company_name: bool | None = None,
    perceptual_distance: int = 0,
    perceptual_similarity: float = 1.0,
) -> LogoFingerprintComparison:
    return LogoFingerprintComparison(
        exact_image_match=True,
        perceptual_distance=perceptual_distance,
        perceptual_similarity=perceptual_similarity,
        average_distance=0,
        average_similarity=1.0,
        difference_distance=0,
        difference_similarity=1.0,
        same_dimensions=True,
        width_difference=0,
        height_difference=0,
        same_company_name=same_company_name,
    )


def test_should_create_logo_fingerprint_comparison(
) -> None:
    comparison = create_comparison(
        same_company_name=True,
    )

    assert comparison.exact_image_match is True
    assert comparison.perceptual_distance == 0
    assert comparison.perceptual_similarity == 1.0
    assert comparison.same_dimensions is True
    assert comparison.same_company_name is True


def test_should_inherit_visual_identity_behavior(
) -> None:
    comparison = create_comparison(
        perceptual_distance=0,
        perceptual_similarity=1.0,
    )

    assert comparison.is_visually_identical is True


def test_should_detect_available_company_name_comparison(
) -> None:
    comparison = create_comparison(
        same_company_name=False,
    )

    assert (
        comparison.has_company_name_comparison
        is True
    )


def test_should_detect_missing_company_name_comparison(
) -> None:
    comparison = create_comparison(
        same_company_name=None,
    )

    assert (
        comparison.has_company_name_comparison
        is False
    )


def test_should_identify_same_company_logo(
) -> None:
    comparison = create_comparison(
        same_company_name=True,
    )

    assert comparison.is_same_company_logo is True


def test_should_not_identify_different_company_as_same(
) -> None:
    comparison = create_comparison(
        same_company_name=False,
    )

    assert comparison.is_same_company_logo is False


def test_should_preserve_image_comparison_validations(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "perceptual_similarity must be "
            "between 0.0 and 1.0."
        ),
    ):
        create_comparison(
            perceptual_similarity=1.1,
        )