from __future__ import annotations

from app.domain.models.image_match_classification import (
    ImageMatchClassification,
)


def test_should_define_none_classification() -> None:
    assert ImageMatchClassification.NONE.value == "none"


def test_should_define_moderate_classification() -> None:
    assert (
        ImageMatchClassification.MODERATE.value
        == "moderate"
    )


def test_should_define_strong_classification() -> None:
    assert (
        ImageMatchClassification.STRONG.value
        == "strong"
    )


def test_should_define_exact_classification() -> None:
    assert ImageMatchClassification.EXACT.value == "exact"


def test_should_behave_as_string_enum() -> None:
    assert ImageMatchClassification.EXACT == "exact"
    assert ImageMatchClassification.STRONG == "strong"