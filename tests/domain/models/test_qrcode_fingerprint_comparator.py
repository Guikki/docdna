from __future__ import annotations

import pytest

from app.domain.comparators.qrcode_fingerprint_comparator import (
    QRCodeFingerprintComparator,
)
from app.domain.fingerprints.qrcode_fingerprint import (
    QRCodeFingerprint,
)
from app.domain.models.qrcode_fingerprint_comparison import (
    QRCodeFingerprintComparison,
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


def make_qrcode(
    *,
    value: str = "PIX|123456789",
    encoding: str | None = "UTF-8",
    version: int | None = 5,
    error_correction: str | None = "M",
    image_hash: str | None = "ABCDEF123456",
    rotation: float = 0.0,
) -> QRCodeFingerprint:
    return QRCodeFingerprint(
        location=DocumentLocation(
            page_number=1,
            bounding_box=BoundingBox(
                x=10,
                y=20,
                width=120,
                height=120,
            ),
        ),
        confidence=ConfidenceScore(0.99),
        value=value,
        encoding=encoding,
        version=version,
        error_correction=error_correction,
        image_hash=image_hash,
        rotation=rotation,
    )


def test_should_return_qrcode_comparison() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(),
        make_qrcode(),
    )

    assert isinstance(
        result,
        QRCodeFingerprintComparison,
    )


def test_should_identify_equal_qrcodes() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(),
        make_qrcode(),
    )

    assert result.exact_image_match is True
    assert result.same_value is True
    assert result.same_encoding is True
    assert result.same_version is True
    assert result.same_error_correction is True
    assert result.rotation_difference == 0.0


def test_should_compare_image_hash_case_insensitively() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            image_hash="ABCDEF",
        ),
        make_qrcode(
            image_hash="abcdef",
        ),
    )

    assert result.exact_image_match is True


def test_should_trim_image_hash_before_comparison() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            image_hash=" abcdef ",
        ),
        make_qrcode(
            image_hash="abcdef",
        ),
    )

    assert result.exact_image_match is True


@pytest.mark.parametrize(
    (
        "first_hash",
        "second_hash",
    ),
    [
        (None, "abcdef"),
        ("abcdef", None),
        (None, None),
        ("", "abcdef"),
        ("abcdef", ""),
        ("   ", "abcdef"),
        ("abcdef", "   "),
    ],
)
def test_should_not_report_exact_image_match_without_valid_hashes(
    first_hash: str | None,
    second_hash: str | None,
) -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            image_hash=first_hash,
        ),
        make_qrcode(
            image_hash=second_hash,
        ),
    )

    assert result.exact_image_match is False


def test_should_identify_different_image_hashes() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            image_hash="abcdef",
        ),
        make_qrcode(
            image_hash="123456",
        ),
    )

    assert result.exact_image_match is False


def test_should_compare_value_case_insensitively() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            value="PAYLOAD-ABC",
        ),
        make_qrcode(
            value="payload-abc",
        ),
    )

    assert result.same_value is True


def test_should_trim_value_before_comparison() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            value=" payload-abc ",
        ),
        make_qrcode(
            value="payload-abc",
        ),
    )

    assert result.same_value is True


def test_should_identify_different_values() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            value="payload-1",
        ),
        make_qrcode(
            value="payload-2",
        ),
    )

    assert result.same_value is False


def test_should_compare_encoding_case_insensitively() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            encoding="UTF-8",
        ),
        make_qrcode(
            encoding="utf-8",
        ),
    )

    assert result.same_encoding is True


def test_should_trim_encoding_before_comparison() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            encoding=" UTF-8 ",
        ),
        make_qrcode(
            encoding="utf-8",
        ),
    )

    assert result.same_encoding is True


def test_should_identify_different_encodings() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            encoding="UTF-8",
        ),
        make_qrcode(
            encoding="ISO-8859-1",
        ),
    )

    assert result.same_encoding is False


@pytest.mark.parametrize(
    (
        "first_encoding",
        "second_encoding",
    ),
    [
        (None, "UTF-8"),
        ("UTF-8", None),
        (None, None),
        ("", "UTF-8"),
        ("UTF-8", ""),
        ("   ", "UTF-8"),
        ("UTF-8", "   "),
    ],
)
def test_should_report_unavailable_encoding_comparison(
    first_encoding: str | None,
    second_encoding: str | None,
) -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            encoding=first_encoding,
        ),
        make_qrcode(
            encoding=second_encoding,
        ),
    )

    assert result.same_encoding is None


def test_should_identify_equal_versions() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            version=5,
        ),
        make_qrcode(
            version=5,
        ),
    )

    assert result.same_version is True


def test_should_identify_different_versions() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            version=5,
        ),
        make_qrcode(
            version=6,
        ),
    )

    assert result.same_version is False


@pytest.mark.parametrize(
    (
        "first_version",
        "second_version",
    ),
    [
        (None, 5),
        (5, None),
        (None, None),
    ],
)
def test_should_report_unavailable_version_comparison(
    first_version: int | None,
    second_version: int | None,
) -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            version=first_version,
        ),
        make_qrcode(
            version=second_version,
        ),
    )

    assert result.same_version is None


def test_should_compare_error_correction_case_insensitively() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            error_correction="M",
        ),
        make_qrcode(
            error_correction="m",
        ),
    )

    assert result.same_error_correction is True


def test_should_trim_error_correction_before_comparison() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            error_correction=" M ",
        ),
        make_qrcode(
            error_correction="m",
        ),
    )

    assert result.same_error_correction is True


def test_should_identify_different_error_correction() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            error_correction="M",
        ),
        make_qrcode(
            error_correction="H",
        ),
    )

    assert result.same_error_correction is False


@pytest.mark.parametrize(
    (
        "first_error_correction",
        "second_error_correction",
    ),
    [
        (None, "M"),
        ("M", None),
        (None, None),
        ("", "M"),
        ("M", ""),
        ("   ", "M"),
        ("M", "   "),
    ],
)
def test_should_report_unavailable_error_correction_comparison(
    first_error_correction: str | None,
    second_error_correction: str | None,
) -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            error_correction=first_error_correction,
        ),
        make_qrcode(
            error_correction=second_error_correction,
        ),
    )

    assert result.same_error_correction is None


@pytest.mark.parametrize(
    (
        "first_rotation",
        "second_rotation",
        "expected_difference",
    ),
    [
        (0.0, 0.0, 0.0),
        (0.0, 90.0, 90.0),
        (90.0, 0.0, 90.0),
        (45.0, 180.0, 135.0),
        (270.0, 90.0, 180.0),
    ],
)
def test_should_calculate_absolute_rotation_difference(
    first_rotation: float,
    second_rotation: float,
    expected_difference: float,
) -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            rotation=first_rotation,
        ),
        make_qrcode(
            rotation=second_rotation,
        ),
    )

    assert (
        result.rotation_difference
        == expected_difference
    )


def test_should_identify_same_value_with_different_image() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            value="same-payload",
            image_hash="image-1",
        ),
        make_qrcode(
            value="same-payload",
            image_hash="image-2",
        ),
    )

    assert result.is_same_qrcode is True
    assert (
        result.is_same_value_with_different_image
        is True
    )


def test_should_identify_equal_image_with_different_value() -> None:
    comparator = QRCodeFingerprintComparator()

    result = comparator.compare(
        make_qrcode(
            value="payload-1",
            image_hash="same-image",
        ),
        make_qrcode(
            value="payload-2",
            image_hash="same-image",
        ),
    )

    assert result.exact_image_match is True
    assert result.same_value is False
    assert (
        result.is_visually_equal_but_value_changed
        is True
    )