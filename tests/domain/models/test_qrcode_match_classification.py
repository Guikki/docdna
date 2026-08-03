from __future__ import annotations

from app.domain.models.qrcode_match_classification import (
    QRCodeMatchClassification,
)


def test_should_define_none_classification() -> None:
    assert QRCodeMatchClassification.NONE.value == "none"


def test_should_define_moderate_classification() -> None:
    assert (
        QRCodeMatchClassification.MODERATE.value
        == "moderate"
    )


def test_should_define_strong_classification() -> None:
    assert (
        QRCodeMatchClassification.STRONG.value
        == "strong"
    )


def test_should_define_exact_classification() -> None:
    assert QRCodeMatchClassification.EXACT.value == "exact"


def test_should_behave_as_string_enum() -> None:
    classification = QRCodeMatchClassification.EXACT

    assert isinstance(classification, str)
    assert classification == "exact"


def test_should_create_classification_from_value() -> None:
    classification = QRCodeMatchClassification(
        "strong"
    )

    assert classification is QRCodeMatchClassification.STRONG