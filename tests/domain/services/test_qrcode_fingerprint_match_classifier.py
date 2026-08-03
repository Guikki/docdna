from __future__ import annotations

import pytest

from app.domain.models.qrcode_fingerprint_comparison import (
    QRCodeFingerprintComparison,
)
from app.domain.models.qrcode_match_classification import (
    QRCodeMatchClassification,
)
from app.domain.services.qrcode_fingerprint_match_classifier import (
    QRCodeFingerprintMatchClassifier,
)


def create_comparison(
    *,
    exact_image_match: bool = False,
    same_value: bool = False,
    same_encoding: bool | None = None,
    same_version: bool | None = None,
    same_error_correction: bool | None = None,
    rotation_difference: float = 0.0,
) -> QRCodeFingerprintComparison:
    return QRCodeFingerprintComparison(
        exact_image_match=exact_image_match,
        same_value=same_value,
        same_encoding=same_encoding,
        same_version=same_version,
        same_error_correction=same_error_correction,
        rotation_difference=rotation_difference,
    )


def test_should_classify_same_qrcode_as_exact() -> None:
    comparison = create_comparison(
        exact_image_match=True,
        same_value=True,
        same_encoding=True,
        same_version=True,
        same_error_correction=True,
    )

    classification = (
        QRCodeFingerprintMatchClassifier().classify(
            comparison
        )
    )

    assert classification is QRCodeMatchClassification.EXACT


def test_should_classify_same_value_as_strong() -> None:
    comparison = create_comparison(
        exact_image_match=False,
        same_value=True,
    )

    classification = (
        QRCodeFingerprintMatchClassifier().classify(
            comparison
        )
    )

    assert classification is QRCodeMatchClassification.STRONG


def test_should_classify_same_image_with_changed_value_as_moderate(
) -> None:
    comparison = create_comparison(
        exact_image_match=True,
        same_value=False,
    )

    classification = (
        QRCodeFingerprintMatchClassifier().classify(
            comparison
        )
    )

    assert (
        classification
        is QRCodeMatchClassification.MODERATE
    )


def test_should_classify_unrelated_qrcodes_as_none() -> None:
    comparison = create_comparison(
        exact_image_match=False,
        same_value=False,
    )

    classification = (
        QRCodeFingerprintMatchClassifier().classify(
            comparison
        )
    )

    assert classification is QRCodeMatchClassification.NONE


@pytest.mark.parametrize(
    (
        "same_encoding",
        "same_version",
        "same_error_correction",
    ),
    [
        (True, True, True),
        (False, True, True),
        (True, False, True),
        (True, True, False),
        (False, False, False),
        (None, None, None),
    ],
)
def test_should_classify_same_value_as_strong_independently_of_metadata(
    same_encoding: bool | None,
    same_version: bool | None,
    same_error_correction: bool | None,
) -> None:
    comparison = create_comparison(
        exact_image_match=False,
        same_value=True,
        same_encoding=same_encoding,
        same_version=same_version,
        same_error_correction=same_error_correction,
    )

    classification = (
        QRCodeFingerprintMatchClassifier().classify(
            comparison
        )
    )

    assert classification is QRCodeMatchClassification.STRONG


@pytest.mark.parametrize(
    (
        "same_encoding",
        "same_version",
        "same_error_correction",
    ),
    [
        (True, True, True),
        (False, True, True),
        (True, False, True),
        (True, True, False),
        (False, False, False),
        (None, None, None),
    ],
)
def test_should_classify_exact_image_with_different_value_as_moderate_independently_of_metadata(
    same_encoding: bool | None,
    same_version: bool | None,
    same_error_correction: bool | None,
) -> None:
    comparison = create_comparison(
        exact_image_match=True,
        same_value=False,
        same_encoding=same_encoding,
        same_version=same_version,
        same_error_correction=same_error_correction,
    )

    classification = (
        QRCodeFingerprintMatchClassifier().classify(
            comparison
        )
    )

    assert (
        classification
        is QRCodeMatchClassification.MODERATE
    )


@pytest.mark.parametrize(
    "rotation_difference",
    [
        0.0,
        45.0,
        90.0,
        180.0,
        270.0,
        360.0,
    ],
)
def test_should_not_change_strong_classification_based_on_rotation(
    rotation_difference: float,
) -> None:
    comparison = create_comparison(
        exact_image_match=False,
        same_value=True,
        rotation_difference=rotation_difference,
    )

    classification = (
        QRCodeFingerprintMatchClassifier().classify(
            comparison
        )
    )

    assert classification is QRCodeMatchClassification.STRONG


@pytest.mark.parametrize(
    "rotation_difference",
    [
        0.0,
        45.0,
        90.0,
        180.0,
        270.0,
        360.0,
    ],
)
def test_should_not_change_none_classification_based_on_rotation(
    rotation_difference: float,
) -> None:
    comparison = create_comparison(
        exact_image_match=False,
        same_value=False,
        rotation_difference=rotation_difference,
    )

    classification = (
        QRCodeFingerprintMatchClassifier().classify(
            comparison
        )
    )

    assert classification is QRCodeMatchClassification.NONE