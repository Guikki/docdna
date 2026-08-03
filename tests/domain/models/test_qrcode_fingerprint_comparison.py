from __future__ import annotations

import pytest

from app.domain.models.qrcode_fingerprint_comparison import (
    QRCodeFingerprintComparison,
)


def make_comparison(
    *,
    exact_image_match: bool = False,
    same_value: bool = True,
    same_encoding: bool | None = True,
    same_version: bool | None = True,
    same_error_correction: bool | None = True,
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


def test_should_store_comparison_values() -> None:
    comparison = make_comparison(
        exact_image_match=True,
        same_value=False,
        same_encoding=True,
        same_version=False,
        same_error_correction=None,
        rotation_difference=90.0,
    )

    assert comparison.exact_image_match is True
    assert comparison.same_value is False
    assert comparison.same_encoding is True
    assert comparison.same_version is False
    assert comparison.same_error_correction is None
    assert comparison.rotation_difference == 90.0


def test_should_identify_same_qrcode_by_value() -> None:
    comparison = make_comparison(
        same_value=True,
    )

    assert comparison.is_same_qrcode is True


def test_should_not_identify_different_value_as_same_qrcode() -> None:
    comparison = make_comparison(
        same_value=False,
    )

    assert comparison.is_same_qrcode is False


def test_should_report_encoding_comparison_available() -> None:
    comparison = make_comparison(
        same_encoding=False,
    )

    assert comparison.has_encoding_comparison is True


def test_should_report_encoding_comparison_unavailable() -> None:
    comparison = make_comparison(
        same_encoding=None,
    )

    assert comparison.has_encoding_comparison is False


def test_should_report_version_comparison_available() -> None:
    comparison = make_comparison(
        same_version=True,
    )

    assert comparison.has_version_comparison is True


def test_should_report_version_comparison_unavailable() -> None:
    comparison = make_comparison(
        same_version=None,
    )

    assert comparison.has_version_comparison is False


def test_should_report_error_correction_comparison_available() -> None:
    comparison = make_comparison(
        same_error_correction=False,
    )

    assert (
        comparison.has_error_correction_comparison
        is True
    )


def test_should_report_error_correction_comparison_unavailable() -> None:
    comparison = make_comparison(
        same_error_correction=None,
    )

    assert (
        comparison.has_error_correction_comparison
        is False
    )


def test_should_identify_same_rotation() -> None:
    comparison = make_comparison(
        rotation_difference=0.0,
    )

    assert comparison.has_same_rotation is True


def test_should_identify_different_rotation() -> None:
    comparison = make_comparison(
        rotation_difference=90.0,
    )

    assert comparison.has_same_rotation is False


def test_should_identify_equal_image_with_changed_value() -> None:
    comparison = make_comparison(
        exact_image_match=True,
        same_value=False,
    )

    assert (
        comparison.is_visually_equal_but_value_changed
        is True
    )


@pytest.mark.parametrize(
    (
        "exact_image_match",
        "same_value",
    ),
    [
        (False, False),
        (False, True),
        (True, True),
    ],
)
def test_should_not_report_changed_value_without_critical_combination(
    exact_image_match: bool,
    same_value: bool,
) -> None:
    comparison = make_comparison(
        exact_image_match=exact_image_match,
        same_value=same_value,
    )

    assert (
        comparison.is_visually_equal_but_value_changed
        is False
    )


def test_should_identify_same_value_with_different_image() -> None:
    comparison = make_comparison(
        exact_image_match=False,
        same_value=True,
    )

    assert (
        comparison.is_same_value_with_different_image
        is True
    )


@pytest.mark.parametrize(
    (
        "exact_image_match",
        "same_value",
    ),
    [
        (False, False),
        (True, False),
        (True, True),
    ],
)
def test_should_not_report_regenerated_qrcode_without_combination(
    exact_image_match: bool,
    same_value: bool,
) -> None:
    comparison = make_comparison(
        exact_image_match=exact_image_match,
        same_value=same_value,
    )

    assert (
        comparison.is_same_value_with_different_image
        is False
    )


def test_should_reject_negative_rotation_difference() -> None:
    with pytest.raises(
        ValueError,
        match="rotation_difference cannot be negative.",
    ):
        make_comparison(
            rotation_difference=-1.0,
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
def test_should_accept_non_negative_rotation_difference(
    rotation_difference: float,
) -> None:
    comparison = make_comparison(
        rotation_difference=rotation_difference,
    )

    assert (
        comparison.rotation_difference
        == rotation_difference
    )