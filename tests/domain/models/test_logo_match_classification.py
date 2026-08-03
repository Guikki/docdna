from __future__ import annotations

import pytest

from app.domain.models.logo_match_classification import (
    LogoMatchClassification,
)


@pytest.mark.parametrize(
    (
        "classification",
        "expected_value",
    ),
    [
        (
            LogoMatchClassification.NONE,
            "none",
        ),
        (
            LogoMatchClassification.MODERATE,
            "moderate",
        ),
        (
            LogoMatchClassification.STRONG,
            "strong",
        ),
        (
            LogoMatchClassification.EXACT,
            "exact",
        ),
    ],
)
def test_should_expose_expected_classification_value(
    classification: LogoMatchClassification,
    expected_value: str,
) -> None:
    assert classification.value == expected_value
    assert isinstance(classification, str)