import pytest

from app.domain.value_objects.confidence_score import (
    ConfidenceScore,
)


def test_percentage():
    score = ConfidenceScore(0.95)

    assert score.percentage == 95.0


def test_high():
    assert ConfidenceScore(0.95).is_high


def test_medium():
    assert ConfidenceScore(0.75).is_medium


def test_low():
    assert ConfidenceScore(0.40).is_low


@pytest.mark.parametrize(
    "value",
    [-0.1, 1.1],
)
def test_invalid_values(value):
    with pytest.raises(ValueError):
        ConfidenceScore(value)