from __future__ import annotations

from typing import Any
from unittest.mock import Mock

from app.domain.comparators.base_comparator import (
    BaseComparator,
)
from app.domain.comparators.qrcode_fingerprint_comparator import (
    QRCodeFingerprintComparator,
)
from app.domain.comparators.qrcode_fingerprint_cross_comparator import (
    QRCodeFingerprintCrossComparator,
)
from app.domain.fingerprints.qrcode_fingerprint import (
    QRCodeFingerprint,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
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
from app.domain.services.qrcode_fingerprint_pair_generator import (
    QRCodeFingerprintPairGenerator,
)


def create_pair(
    *,
    first_document_id: str = "document-1",
    second_document_id: str = "document-2",
) -> QRCodeFingerprintPair:
    first_qrcode = Mock(
        spec=QRCodeFingerprint
    )

    second_qrcode = Mock(
        spec=QRCodeFingerprint
    )

    return QRCodeFingerprintPair(
        first_document_id=first_document_id,
        second_document_id=second_document_id,
        first_qrcode=first_qrcode,
        second_qrcode=second_qrcode,
    )


def create_comparison(
    *,
    same_value: bool = True,
    exact_image_match: bool = True,
) -> QRCodeFingerprintComparison:
    return QRCodeFingerprintComparison(
        exact_image_match=exact_image_match,
        same_value=same_value,
        same_encoding=True,
        same_version=True,
        same_error_correction=True,
        rotation_difference=0.0,
    )


def create_finding(
    *,
    code: str = "QRCODE_EXACT_MATCH",
    first_document_id: str = "document-1",
    second_document_id: str = "document-2",
) -> CrossValidationFinding:
    return CrossValidationFinding(
        code=code,
        title="Finding de teste",
        description="Descrição do finding de teste.",
        severity=CrossValidationSeverity.INFO,
        confidence=1.0,
        comparator="QRCodeFingerprintCrossComparator",
        document_ids=[
            first_document_id,
            second_document_id,
        ],
        metadata={},
    )


def test_should_implement_base_comparator() -> None:
    comparator = QRCodeFingerprintCrossComparator()

    assert isinstance(
        comparator,
        BaseComparator,
    )


def test_should_create_default_dependencies() -> None:
    comparator = QRCodeFingerprintCrossComparator()

    assert isinstance(
        comparator._pair_generator,
        QRCodeFingerprintPairGenerator,
    )

    assert isinstance(
        comparator._qrcode_comparator,
        QRCodeFingerprintComparator,
    )

    assert isinstance(
        comparator._finding_builder,
        QRCodeFingerprintFindingBuilder,
    )


def test_should_send_analyses_to_pair_generator() -> None:
    analyses: list[dict[str, Any]] = [
        {
            "id": "document-1",
            "qrcode_fingerprints": [],
        },
        {
            "id": "document-2",
            "qrcode_fingerprints": [],
        },
    ]

    pair_generator = Mock(
        spec=QRCodeFingerprintPairGenerator
    )

    pair_generator.generate.return_value = []

    qrcode_comparator = Mock(
        spec=QRCodeFingerprintComparator
    )

    finding_builder = Mock(
        spec=QRCodeFingerprintFindingBuilder
    )

    comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare(
        analyses
    )

    pair_generator.generate.assert_called_once_with(
        analyses
    )

    assert result == []


def test_should_not_compare_qrcodes_when_no_pairs_exist() -> None:
    pair_generator = Mock(
        spec=QRCodeFingerprintPairGenerator
    )

    pair_generator.generate.return_value = []

    qrcode_comparator = Mock(
        spec=QRCodeFingerprintComparator
    )

    finding_builder = Mock(
        spec=QRCodeFingerprintFindingBuilder
    )

    comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    qrcode_comparator.compare.assert_not_called()
    finding_builder.build.assert_not_called()

    assert result == []


def test_should_compare_qrcodes_from_generated_pair() -> None:
    pair = create_pair()
    comparison = create_comparison()

    pair_generator = Mock(
        spec=QRCodeFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        pair
    ]

    qrcode_comparator = Mock(
        spec=QRCodeFingerprintComparator
    )

    qrcode_comparator.compare.return_value = (
        comparison
    )

    finding_builder = Mock(
        spec=QRCodeFingerprintFindingBuilder
    )

    finding_builder.build.return_value = []

    comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    comparator.compare([])

    qrcode_comparator.compare.assert_called_once_with(
        pair.first_qrcode,
        pair.second_qrcode,
    )


def test_should_send_comparison_to_finding_builder() -> None:
    pair = create_pair()
    comparison = create_comparison()

    pair_generator = Mock(
        spec=QRCodeFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        pair
    ]

    qrcode_comparator = Mock(
        spec=QRCodeFingerprintComparator
    )

    qrcode_comparator.compare.return_value = (
        comparison
    )

    finding_builder = Mock(
        spec=QRCodeFingerprintFindingBuilder
    )

    finding_builder.build.return_value = []

    comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    comparator.compare([])

    finding_builder.build.assert_called_once_with(
        pair=pair,
        comparison=comparison,
        comparator=(
            "QRCodeFingerprintCrossComparator"
        ),
    )


def test_should_return_findings_created_by_builder() -> None:
    pair = create_pair()
    comparison = create_comparison()
    finding = create_finding()

    pair_generator = Mock(
        spec=QRCodeFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        pair
    ]

    qrcode_comparator = Mock(
        spec=QRCodeFingerprintComparator
    )

    qrcode_comparator.compare.return_value = (
        comparison
    )

    finding_builder = Mock(
        spec=QRCodeFingerprintFindingBuilder
    )

    finding_builder.build.return_value = [
        finding
    ]

    comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    assert result == [
        finding
    ]


def test_should_aggregate_findings_from_multiple_pairs() -> None:
    first_pair = create_pair(
        first_document_id="document-1",
        second_document_id="document-2",
    )

    second_pair = create_pair(
        first_document_id="document-1",
        second_document_id="document-3",
    )

    first_comparison = create_comparison(
        same_value=True,
        exact_image_match=True,
    )

    second_comparison = create_comparison(
        same_value=True,
        exact_image_match=False,
    )

    first_finding = create_finding(
        code="QRCODE_EXACT_MATCH",
        first_document_id="document-1",
        second_document_id="document-2",
    )

    second_finding = create_finding(
        code="QRCODE_REGENERATED",
        first_document_id="document-1",
        second_document_id="document-3",
    )

    pair_generator = Mock(
        spec=QRCodeFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        first_pair,
        second_pair,
    ]

    qrcode_comparator = Mock(
        spec=QRCodeFingerprintComparator
    )

    qrcode_comparator.compare.side_effect = [
        first_comparison,
        second_comparison,
    ]

    finding_builder = Mock(
        spec=QRCodeFingerprintFindingBuilder
    )

    finding_builder.build.side_effect = [
        [first_finding],
        [second_finding],
    ]

    comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    assert result == [
        first_finding,
        second_finding,
    ]

    assert (
        qrcode_comparator.compare.call_count
        == 2
    )

    assert finding_builder.build.call_count == 2


def test_should_ignore_pair_when_builder_returns_no_finding() -> None:
    first_pair = create_pair(
        first_document_id="document-1",
        second_document_id="document-2",
    )

    second_pair = create_pair(
        first_document_id="document-1",
        second_document_id="document-3",
    )

    first_comparison = create_comparison(
        same_value=True,
        exact_image_match=True,
    )

    second_comparison = create_comparison(
        same_value=False,
        exact_image_match=False,
    )

    finding = create_finding()

    pair_generator = Mock(
        spec=QRCodeFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        first_pair,
        second_pair,
    ]

    qrcode_comparator = Mock(
        spec=QRCodeFingerprintComparator
    )

    qrcode_comparator.compare.side_effect = [
        first_comparison,
        second_comparison,
    ]

    finding_builder = Mock(
        spec=QRCodeFingerprintFindingBuilder
    )

    finding_builder.build.side_effect = [
        [finding],
        [],
    ]

    comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    assert result == [
        finding
    ]