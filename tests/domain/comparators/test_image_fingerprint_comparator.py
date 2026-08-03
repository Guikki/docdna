from __future__ import annotations

import pytest

from app.domain.comparators.image_fingerprint_comparator import (
    ImageFingerprintComparator,
)
from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.document_location import DocumentLocation


def create_fingerprint(
    *,
    perceptual_hash: str = "0000000000000000",
    average_hash: str | None = "0000000000000000",
    difference_hash: str | None = "0000000000000000",
    image_hash: str | None = "a" * 64,
    width: int = 640,
    height: int = 480,
    page_number: int = 1,
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


def test_should_compare_identical_fingerprints() -> None:
    first = create_fingerprint()
    second = create_fingerprint()

    comparator = ImageFingerprintComparator()

    result = comparator.compare(first, second)

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

    assert result.is_visually_identical is True


def test_should_calculate_perceptual_hash_distance() -> None:
    first = create_fingerprint(
        perceptual_hash="0000000000000000",
    )

    second = create_fingerprint(
        perceptual_hash="000000000000000f",
        image_hash="b" * 64,
    )

    result = ImageFingerprintComparator().compare(
        first,
        second,
    )

    assert result.perceptual_distance == 4
    assert result.perceptual_similarity == pytest.approx(
        60 / 64,
    )

    assert result.exact_image_match is False
    assert result.is_visually_identical is False


def test_should_compare_completely_different_hashes() -> None:
    first = create_fingerprint(
        perceptual_hash="0000000000000000",
    )

    second = create_fingerprint(
        perceptual_hash="ffffffffffffffff",
    )

    result = ImageFingerprintComparator().compare(
        first,
        second,
    )

    assert result.perceptual_distance == 64
    assert result.perceptual_similarity == 0.0


def test_should_compare_optional_hashes_independently() -> None:
    first = create_fingerprint(
        average_hash="0000000000000000",
        difference_hash="0000000000000000",
    )

    second = create_fingerprint(
        average_hash="0000000000000003",
        difference_hash="0000000000000007",
    )

    result = ImageFingerprintComparator().compare(
        first,
        second,
    )

    assert result.average_distance == 2
    assert result.average_similarity == pytest.approx(
        62 / 64,
    )

    assert result.difference_distance == 3
    assert result.difference_similarity == pytest.approx(
        61 / 64,
    )


def test_should_skip_optional_metric_when_one_hash_is_missing() -> None:
    first = create_fingerprint(
        average_hash=None,
        difference_hash="0000000000000000",
    )

    second = create_fingerprint(
        average_hash="0000000000000000",
        difference_hash=None,
    )

    result = ImageFingerprintComparator().compare(
        first,
        second,
    )

    assert result.average_distance is None
    assert result.average_similarity is None

    assert result.difference_distance is None
    assert result.difference_similarity is None

    assert result.has_average_hash_comparison is False
    assert result.has_difference_hash_comparison is False


def test_should_not_report_exact_match_without_sha256() -> None:
    first = create_fingerprint(
        image_hash=None,
    )

    second = create_fingerprint(
        image_hash=None,
    )

    result = ImageFingerprintComparator().compare(
        first,
        second,
    )

    assert result.exact_image_match is False


def test_should_normalize_hash_case_and_whitespace() -> None:
    first = create_fingerprint(
        perceptual_hash=" ABCDEF0000000000 ",
        image_hash=" AABBCC ",
    )

    second = create_fingerprint(
        perceptual_hash="abcdef0000000000",
        image_hash="aabbcc",
    )

    result = ImageFingerprintComparator().compare(
        first,
        second,
    )

    assert result.perceptual_distance == 0
    assert result.perceptual_similarity == 1.0
    assert result.exact_image_match is True


def test_should_calculate_dimension_differences() -> None:
    first = create_fingerprint(
        width=640,
        height=480,
    )

    second = create_fingerprint(
        width=1920,
        height=1080,
    )

    result = ImageFingerprintComparator().compare(
        first,
        second,
    )

    assert result.same_dimensions is False
    assert result.width_difference == 1280
    assert result.height_difference == 600


def test_should_reject_hashes_with_different_lengths() -> None:
    first = create_fingerprint(
        perceptual_hash="0000000000000000",
    )

    second = create_fingerprint(
        perceptual_hash="00000000",
    )

    with pytest.raises(
        ValueError,
        match=(
            "perceptual_hash values must have the same length"
        ),
    ):
        ImageFingerprintComparator().compare(
            first,
            second,
        )


def test_should_reject_non_hexadecimal_hash() -> None:
    first = create_fingerprint(
        perceptual_hash="not-a-valid-hash",
    )

    second = create_fingerprint()

    with pytest.raises(
        ValueError,
        match=(
            "perceptual_hash must be a hexadecimal string"
        ),
    ):
        ImageFingerprintComparator().compare(
            first,
            second,
        )