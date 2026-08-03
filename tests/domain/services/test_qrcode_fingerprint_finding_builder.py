from __future__ import annotations

import pytest

from app.domain.fingerprints.qrcode_fingerprint import (
    QRCodeFingerprint,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationSeverity,
)
from app.domain.models.qrcode_fingerprint_comparison import (
    QRCodeFingerprintComparison,
)
from app.domain.models.qrcode_fingerprint_pair import (
    QRCodeFingerprintPair,
)
from app.domain.services.qrcode_fingerprint_finding_builder import (
    QRCodeFingerprintFindingBuilder,
)
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from app.domain.value_objects.document_location import (
    DocumentLocation,
)


def create_fingerprint(
    *,
    page_number: int,
    value: str,
    image_hash: str | None,
    encoding: str | None = "utf-8",
    version: int | None = 5,
    error_correction: str | None = "M",
    rotation: float = 0.0,
) -> QRCodeFingerprint:
    return QRCodeFingerprint(
        location=DocumentLocation(
            page_number=page_number,
            bounding_box=BoundingBox(
                x=10.0,
                y=20.0,
                width=150.0,
                height=150.0,
            ),
        ),
        confidence=ConfidenceScore(1.0),
        value=value,
        encoding=encoding,
        version=version,
        error_correction=error_correction,
        image_hash=image_hash,
        rotation=rotation,
    )


def create_pair(
    *,
    first_value: str = "https://example.com/payment/123",
    second_value: str = "https://example.com/payment/123",
    first_image_hash: str | None = "a" * 64,
    second_image_hash: str | None = "a" * 64,
    first_encoding: str | None = "utf-8",
    second_encoding: str | None = "utf-8",
    first_version: int | None = 5,
    second_version: int | None = 5,
    first_error_correction: str | None = "M",
    second_error_correction: str | None = "M",
    first_rotation: float = 0.0,
    second_rotation: float = 0.0,
) -> QRCodeFingerprintPair:
    return QRCodeFingerprintPair(
        first_document_id="document-1",
        second_document_id="document-2",
        first_qrcode=create_fingerprint(
            page_number=1,
            value=first_value,
            image_hash=first_image_hash,
            encoding=first_encoding,
            version=first_version,
            error_correction=first_error_correction,
            rotation=first_rotation,
        ),
        second_qrcode=create_fingerprint(
            page_number=2,
            value=second_value,
            image_hash=second_image_hash,
            encoding=second_encoding,
            version=second_version,
            error_correction=second_error_correction,
            rotation=second_rotation,
        ),
    )


def create_comparison(
    *,
    same_value: bool,
    exact_image_match: bool,
    same_encoding: bool | None = True,
    same_version: bool | None = True,
    same_error_correction: bool | None = True,
    rotation_difference: float = 0.0,
) -> QRCodeFingerprintComparison:
    return QRCodeFingerprintComparison(
        same_value=same_value,
        exact_image_match=exact_image_match,
        same_encoding=same_encoding,
        same_version=same_version,
        same_error_correction=same_error_correction,
        rotation_difference=rotation_difference,
    )


def test_should_build_exact_qrcode_match_finding() -> None:
    pair = create_pair()

    comparison = create_comparison(
        same_value=True,
        exact_image_match=True,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=pair,
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "QRCODE_EXACT_MATCH"
    assert finding.title == "QR Code idêntico localizado"
    assert finding.severity is CrossValidationSeverity.INFO
    assert finding.confidence == 1.0

    assert finding.comparator == (
        "QRCodeFingerprintCrossComparator"
    )

    assert finding.document_ids == [
        "document-1",
        "document-2",
    ]


def test_should_build_regenerated_qrcode_finding() -> None:
    pair = create_pair(
        first_image_hash="a" * 64,
        second_image_hash="b" * 64,
    )

    comparison = create_comparison(
        same_value=True,
        exact_image_match=False,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=pair,
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "QRCODE_REGENERATED"
    assert finding.title == (
        "QR Code possivelmente regenerado"
    )
    assert finding.severity is CrossValidationSeverity.LOW
    assert finding.confidence == 1.0


def test_should_build_value_mismatch_finding() -> None:
    pair = create_pair(
        first_value="payment-123",
        second_value="payment-999",
        first_image_hash="a" * 64,
        second_image_hash="a" * 64,
    )

    comparison = create_comparison(
        same_value=False,
        exact_image_match=True,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=pair,
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    assert len(findings) == 1

    finding = findings[0]

    assert finding.code == "QRCODE_VALUE_MISMATCH"
    assert finding.title == (
        "QR Code visualmente idêntico com conteúdo divergente"
    )
    assert finding.severity is CrossValidationSeverity.HIGH
    assert finding.confidence == 1.0


def test_value_mismatch_should_have_priority_over_match_classification(
) -> None:
    comparison = create_comparison(
        same_value=False,
        exact_image_match=True,
        same_encoding=True,
        same_version=True,
        same_error_correction=True,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=create_pair(
            first_value="first-value",
            second_value="second-value",
        ),
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    assert len(findings) == 1
    assert findings[0].code == "QRCODE_VALUE_MISMATCH"
    assert findings[0].severity is CrossValidationSeverity.HIGH


def test_should_not_build_finding_when_qrcodes_are_different(
) -> None:
    comparison = create_comparison(
        same_value=False,
        exact_image_match=False,
        same_encoding=False,
        same_version=False,
        same_error_correction=False,
        rotation_difference=90.0,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=create_pair(
            first_value="first-value",
            second_value="second-value",
            first_image_hash="a" * 64,
            second_image_hash="b" * 64,
        ),
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    assert findings == []


def test_should_include_comparison_metadata() -> None:
    comparison = create_comparison(
        same_value=True,
        exact_image_match=False,
        same_encoding=True,
        same_version=False,
        same_error_correction=True,
        rotation_difference=90.0,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=create_pair(
            first_image_hash="a" * 64,
            second_image_hash="b" * 64,
            first_version=5,
            second_version=6,
            first_rotation=0.0,
            second_rotation=90.0,
        ),
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    metadata = findings[0].metadata

    assert metadata["classification"] == "strong"
    assert metadata["same_value"] is True
    assert metadata["exact_image_match"] is False
    assert metadata["same_encoding"] is True
    assert metadata["same_version"] is False
    assert metadata["same_error_correction"] is True
    assert metadata["rotation_difference"] == 90.0


def test_should_include_semantic_metadata_flags() -> None:
    comparison = create_comparison(
        same_value=True,
        exact_image_match=False,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=create_pair(
            first_image_hash="a" * 64,
            second_image_hash="b" * 64,
        ),
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    metadata = findings[0].metadata

    assert metadata["is_same_qrcode"] is True

    assert (
        metadata["is_same_value_with_different_image"]
        is True
    )

    assert (
        metadata["is_visually_equal_but_value_changed"]
        is False
    )


def test_should_include_comparison_availability_metadata(
) -> None:
    comparison = create_comparison(
        same_value=True,
        exact_image_match=False,
        same_encoding=None,
        same_version=None,
        same_error_correction=None,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=create_pair(
            first_image_hash="a" * 64,
            second_image_hash="b" * 64,
            first_encoding=None,
            second_encoding=None,
            first_version=None,
            second_version=None,
            first_error_correction=None,
            second_error_correction=None,
        ),
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    metadata = findings[0].metadata

    assert metadata["has_encoding_comparison"] is False
    assert metadata["has_version_comparison"] is False

    assert (
        metadata["has_error_correction_comparison"]
        is False
    )


def test_should_include_first_qrcode_metadata() -> None:
    comparison = create_comparison(
        same_value=True,
        exact_image_match=False,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=create_pair(
            first_image_hash="a" * 64,
            second_image_hash="b" * 64,
        ),
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    first_qrcode = findings[0].metadata["first_qrcode"]

    assert first_qrcode["page_number"] == 1
    assert first_qrcode["value"] == (
        "https://example.com/payment/123"
    )
    assert first_qrcode["encoding"] == "utf-8"
    assert first_qrcode["version"] == 5
    assert first_qrcode["error_correction"] == "M"
    assert first_qrcode["image_hash"] == "a" * 64
    assert first_qrcode["rotation"] == 0.0


def test_should_include_second_qrcode_metadata() -> None:
    comparison = create_comparison(
        same_value=True,
        exact_image_match=False,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=create_pair(
            first_image_hash="a" * 64,
            second_image_hash="b" * 64,
            second_rotation=90.0,
        ),
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    second_qrcode = findings[0].metadata["second_qrcode"]

    assert second_qrcode["page_number"] == 2
    assert second_qrcode["value"] == (
        "https://example.com/payment/123"
    )
    assert second_qrcode["encoding"] == "utf-8"
    assert second_qrcode["version"] == 5
    assert second_qrcode["error_correction"] == "M"
    assert second_qrcode["image_hash"] == "b" * 64
    assert second_qrcode["rotation"] == 90.0


def test_should_indicate_same_rotation_in_metadata() -> None:
    comparison = create_comparison(
        same_value=True,
        exact_image_match=True,
        rotation_difference=0.0,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=create_pair(),
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )

    assert findings[0].metadata["has_same_rotation"] is True


def test_should_normalize_comparator_name() -> None:
    comparison = create_comparison(
        same_value=True,
        exact_image_match=True,
    )

    findings = QRCodeFingerprintFindingBuilder().build(
        pair=create_pair(),
        comparison=comparison,
        comparator=(
            "  QRCodeFingerprintCrossComparator  "
        ),
    )

    assert findings[0].comparator == (
        "QRCodeFingerprintCrossComparator"
    )


@pytest.mark.parametrize(
    "comparator",
    [
        "",
        "   ",
    ],
)
def test_should_reject_empty_comparator_name(
    comparator: str,
) -> None:
    comparison = create_comparison(
        same_value=True,
        exact_image_match=True,
    )

    with pytest.raises(
        ValueError,
        match="comparator cannot be empty",
    ):
        QRCodeFingerprintFindingBuilder().build(
            pair=create_pair(),
            comparison=comparison,
            comparator=comparator,
        )