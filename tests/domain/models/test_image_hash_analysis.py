import pytest

from app.domain.models.image_hash_analysis import ImageHashAnalysis


def test_should_create_image_hash_analysis() -> None:
    analysis = ImageHashAnalysis(
        perceptual_hash="8000000000000000",
        average_hash="ffffffffffffffff",
        difference_hash="0000000000000000",
        image_hash="a" * 64,
    )

    assert analysis.perceptual_hash == "8000000000000000"
    assert analysis.average_hash == "ffffffffffffffff"
    assert analysis.difference_hash == "0000000000000000"
    assert analysis.image_hash == "a" * 64


@pytest.mark.parametrize(
    "field_name",
    [
        "perceptual_hash",
        "average_hash",
        "difference_hash",
        "image_hash",
    ],
)
def test_should_reject_empty_hash(
    field_name: str,
) -> None:
    values = {
        "perceptual_hash": "8000000000000000",
        "average_hash": "ffffffffffffffff",
        "difference_hash": "0000000000000000",
        "image_hash": "a" * 64,
    }

    values[field_name] = "   "

    with pytest.raises(
        ValueError,
        match=f"{field_name} cannot be empty",
    ):
        ImageHashAnalysis(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "perceptual_hash",
        "average_hash",
        "difference_hash",
        "image_hash",
    ],
)
def test_should_reject_non_string_hash(
    field_name: str,
) -> None:
    values = {
        "perceptual_hash": "8000000000000000",
        "average_hash": "ffffffffffffffff",
        "difference_hash": "0000000000000000",
        "image_hash": "a" * 64,
    }

    values[field_name] = None

    with pytest.raises(
        TypeError,
        match=f"{field_name} must be a string",
    ):
        ImageHashAnalysis(**values)