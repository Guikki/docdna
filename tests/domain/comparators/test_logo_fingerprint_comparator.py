from __future__ import annotations

import pytest

from app.domain.comparators.logo_fingerprint_comparator import (
    LogoFingerprintComparator,
)
from app.domain.fingerprints.logo_fingerprint import (
    LogoFingerprint,
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


def create_logo(
    *,
    company_name: str | None = "OpenAI",
    perceptual_hash: str = "0000000000000000",
    average_hash: str | None = "0000000000000000",
    difference_hash: str | None = "0000000000000000",
    image_hash: str | None = "exact-image-hash",
    width: int = 100,
    height: int = 50,
) -> LogoFingerprint:
    return LogoFingerprint(
        location=DocumentLocation(
            page_number=1,
            bounding_box=BoundingBox(
                x=0,
                y=0,
                width=100,
                height=50,
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
        company_name=company_name,
    )


def test_should_compare_identical_logos() -> None:
    first = create_logo()
    second = create_logo()

    comparator = LogoFingerprintComparator()

    result = comparator.compare(
        first,
        second,
    )

    assert result.exact_image_match is True

    assert result.perceptual_distance == 0
    assert result.perceptual_similarity == 1.0

    assert result.average_distance == 0
    assert result.average_similarity == 1.0

    assert result.difference_distance == 0
    assert result.difference_similarity == 1.0

    assert result.same_dimensions is True
    assert result.width_difference == 0
    assert result.height_difference == 0

    assert result.same_company_name is True


def test_should_compare_different_perceptual_hashes(
) -> None:
    first = create_logo(
        perceptual_hash="0000000000000000",
    )

    second = create_logo(
        perceptual_hash="ffffffffffffffff",
    )

    result = LogoFingerprintComparator().compare(
        first,
        second,
    )

    assert result.perceptual_distance == 64
    assert result.perceptual_similarity == 0.0
    assert result.is_visually_identical is False


def test_should_preserve_partial_visual_similarity(
) -> None:
    first = create_logo(
        perceptual_hash="0000000000000000",
    )

    second = create_logo(
        perceptual_hash="000000000000000f",
    )

    result = LogoFingerprintComparator().compare(
        first,
        second,
    )

    assert result.perceptual_distance == 4
    assert result.perceptual_similarity == pytest.approx(
        0.9375
    )


def test_should_compare_different_dimensions(
) -> None:
    first = create_logo(
        width=100,
        height=50,
    )

    second = create_logo(
        width=130,
        height=80,
    )

    result = LogoFingerprintComparator().compare(
        first,
        second,
    )

    assert result.same_dimensions is False
    assert result.width_difference == 30
    assert result.height_difference == 30


def test_should_not_consider_missing_image_hash_exact(
) -> None:
    first = create_logo(
        image_hash=None,
    )

    second = create_logo(
        image_hash=None,
    )

    result = LogoFingerprintComparator().compare(
        first,
        second,
    )

    assert result.exact_image_match is False


def test_should_ignore_case_and_external_spaces_in_company_name(
) -> None:
    first = create_logo(
        company_name="  OpenAI  ",
    )

    second = create_logo(
        company_name="openai",
    )

    result = LogoFingerprintComparator().compare(
        first,
        second,
    )

    assert result.same_company_name is True
    assert result.has_company_name_comparison is True
    assert result.is_same_company_logo is True


def test_should_identify_different_company_names(
) -> None:
    first = create_logo(
        company_name="OpenAI",
    )

    second = create_logo(
        company_name="Microsoft",
    )

    result = LogoFingerprintComparator().compare(
        first,
        second,
    )

    assert result.same_company_name is False
    assert result.has_company_name_comparison is True
    assert result.is_same_company_logo is False


@pytest.mark.parametrize(
    (
        "first_company_name",
        "second_company_name",
    ),
    [
        (
            None,
            "OpenAI",
        ),
        (
            "OpenAI",
            None,
        ),
        (
            None,
            None,
        ),
        (
            "",
            "OpenAI",
        ),
        (
            "OpenAI",
            "",
        ),
        (
            "   ",
            "OpenAI",
        ),
        (
            "OpenAI",
            "   ",
        ),
    ],
)
def test_should_not_compare_company_name_when_missing(
    first_company_name: str | None,
    second_company_name: str | None,
) -> None:
    first = create_logo(
        company_name=first_company_name,
    )

    second = create_logo(
        company_name=second_company_name,
    )

    result = LogoFingerprintComparator().compare(
        first,
        second,
    )

    assert result.same_company_name is None
    assert result.has_company_name_comparison is False
    assert result.is_same_company_logo is False


def test_should_not_calculate_missing_optional_hashes(
) -> None:
    first = create_logo(
        average_hash=None,
        difference_hash=None,
    )

    second = create_logo(
        average_hash=None,
        difference_hash=None,
    )

    result = LogoFingerprintComparator().compare(
        first,
        second,
    )

    assert result.average_distance is None
    assert result.average_similarity is None

    assert result.difference_distance is None
    assert result.difference_similarity is None

    assert result.has_average_hash_comparison is False
    assert result.has_difference_hash_comparison is False


def test_should_propagate_invalid_perceptual_hash_error(
) -> None:
    first = create_logo(
        perceptual_hash="not-hexadecimal",
    )

    second = create_logo(
        perceptual_hash="0000000000000000",
    )

    comparator = LogoFingerprintComparator()

    with pytest.raises(
        ValueError,
        match=(
            "perceptual_hash must be "
            "a hexadecimal string."
        ),
    ):
        comparator.compare(
            first,
            second,
        )


def test_should_propagate_different_hash_length_error(
) -> None:
    first = create_logo(
        perceptual_hash="0000",
    )

    second = create_logo(
        perceptual_hash="00000000",
    )

    comparator = LogoFingerprintComparator()

    with pytest.raises(
        ValueError,
        match=(
            "perceptual_hash values must "
            "have the same length."
        ),
    ):
        comparator.compare(
            first,
            second,
        )