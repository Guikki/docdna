import pytest

from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)


def create_comparison(
    **changes: object,
) -> ImageFingerprintComparison:
    data = {
        "exact_image_match": False,
        "perceptual_distance": 4,
        "perceptual_similarity": 0.9375,
        "average_distance": 2,
        "average_similarity": 0.96875,
        "difference_distance": 3,
        "difference_similarity": 0.953125,
        "same_dimensions": True,
        "width_difference": 0,
        "height_difference": 0,
    }

    data.update(changes)

    return ImageFingerprintComparison(**data)


def test_should_create_image_fingerprint_comparison() -> None:
    comparison = create_comparison()

    assert comparison.exact_image_match is False
    assert comparison.perceptual_distance == 4
    assert comparison.perceptual_similarity == 0.9375

    assert comparison.has_average_hash_comparison is True
    assert comparison.has_difference_hash_comparison is True

    assert comparison.same_dimensions is True
    assert comparison.width_difference == 0
    assert comparison.height_difference == 0


def test_should_identify_visually_identical_images() -> None:
    comparison = create_comparison(
        perceptual_distance=0,
        perceptual_similarity=1.0,
    )

    assert comparison.is_visually_identical is True


def test_should_accept_missing_optional_metrics() -> None:
    comparison = create_comparison(
        average_distance=None,
        average_similarity=None,
        difference_distance=None,
        difference_similarity=None,
    )

    assert comparison.has_average_hash_comparison is False
    assert comparison.has_difference_hash_comparison is False


@pytest.mark.parametrize(
    "field_name",
    [
        "perceptual_distance",
        "average_distance",
        "difference_distance",
        "width_difference",
        "height_difference",
    ],
)
def test_should_reject_negative_distances(
    field_name: str,
) -> None:
    with pytest.raises(ValueError):
        create_comparison(
            **{field_name: -1},
        )


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("perceptual_similarity", -0.01),
        ("perceptual_similarity", 1.01),
        ("average_similarity", -0.01),
        ("average_similarity", 1.01),
        ("difference_similarity", -0.01),
        ("difference_similarity", 1.01),
    ],
)
def test_should_reject_similarity_outside_valid_range(
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(ValueError):
        create_comparison(
            **{field_name: value},
        )


def test_should_require_both_average_metrics() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "average_distance and average_similarity "
            "must both be informed or both be None"
        ),
    ):
        create_comparison(
            average_distance=2,
            average_similarity=None,
        )


def test_should_require_both_difference_metrics() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "difference_distance and difference_similarity "
            "must both be informed or both be None"
        ),
    ):
        create_comparison(
            difference_distance=None,
            difference_similarity=0.9,
        )