from __future__ import annotations

from unittest.mock import Mock, call

from app.domain.comparators.qrcode_fingerprint_cross_comparator import (
    QRCodeFingerprintCrossComparator,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)


def create_pair(
    *,
    first_qrcode: object,
    second_qrcode: object,
) -> Mock:
    pair = Mock()

    pair.first_document_id = "document-1"
    pair.second_document_id = "document-2"

    pair.first_qrcode = first_qrcode
    pair.second_qrcode = second_qrcode

    return pair


def create_finding(
    *,
    code: str = "QRCODE_EXACT_MATCH",
) -> CrossValidationFinding:
    return CrossValidationFinding(
        code=code,
        title="QR Code localizado",
        description=(
            "Finding utilizado para validar a orquestração "
            "do comparador cruzado de QR Codes."
        ),
        severity=CrossValidationSeverity.INFO,
        confidence=1.0,
        comparator="QRCodeFingerprintCrossComparator",
        document_ids=[
            "document-1",
            "document-2",
        ],
        metadata={},
    )


def test_should_generate_pairs_from_analyses() -> None:
    analyses = [
        {
            "document_id": "document-1",
            "fingerprints": [],
        },
        {
            "document_id": "document-2",
            "fingerprints": [],
        },
    ]

    pair_generator = Mock()
    pair_generator.generate.return_value = []

    qrcode_comparator = Mock()
    finding_builder = Mock()

    cross_comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    findings = cross_comparator.compare(analyses)

    pair_generator.generate.assert_called_once_with(
        analyses
    )

    assert findings == []


def test_should_compare_qrcodes_from_each_pair() -> None:
    first_qrcode = object()
    second_qrcode = object()

    pair = create_pair(
        first_qrcode=first_qrcode,
        second_qrcode=second_qrcode,
    )

    comparison = object()

    pair_generator = Mock()
    pair_generator.generate.return_value = [pair]

    qrcode_comparator = Mock()
    qrcode_comparator.compare.return_value = comparison

    finding_builder = Mock()
    finding_builder.build.return_value = []

    cross_comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    findings = cross_comparator.compare(
        [
            {
                "document_id": "document-1",
            },
            {
                "document_id": "document-2",
            },
        ]
    )

    qrcode_comparator.compare.assert_called_once_with(
        first_qrcode,
        second_qrcode,
    )

    assert findings == []


def test_should_send_pair_and_comparison_to_finding_builder(
) -> None:
    first_qrcode = object()
    second_qrcode = object()

    pair = create_pair(
        first_qrcode=first_qrcode,
        second_qrcode=second_qrcode,
    )

    comparison = object()

    pair_generator = Mock()
    pair_generator.generate.return_value = [pair]

    qrcode_comparator = Mock()
    qrcode_comparator.compare.return_value = comparison

    finding_builder = Mock()
    finding_builder.build.return_value = []

    cross_comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    cross_comparator.compare(
        [
            {
                "document_id": "document-1",
            },
            {
                "document_id": "document-2",
            },
        ]
    )

    finding_builder.build.assert_called_once_with(
        pair=pair,
        comparison=comparison,
        comparator="QRCodeFingerprintCrossComparator",
    )


def test_should_return_findings_created_by_builder() -> None:
    pair = create_pair(
        first_qrcode=object(),
        second_qrcode=object(),
    )

    comparison = object()
    finding = create_finding()

    pair_generator = Mock()
    pair_generator.generate.return_value = [pair]

    qrcode_comparator = Mock()
    qrcode_comparator.compare.return_value = comparison

    finding_builder = Mock()
    finding_builder.build.return_value = [finding]

    cross_comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    findings = cross_comparator.compare(
        [
            {
                "document_id": "document-1",
            },
            {
                "document_id": "document-2",
            },
        ]
    )

    assert findings == [finding]


def test_should_accumulate_findings_from_multiple_pairs(
) -> None:
    first_pair = create_pair(
        first_qrcode=object(),
        second_qrcode=object(),
    )

    second_pair = create_pair(
        first_qrcode=object(),
        second_qrcode=object(),
    )

    first_comparison = object()
    second_comparison = object()

    first_finding = create_finding(
        code="QRCODE_EXACT_MATCH",
    )

    second_finding = create_finding(
        code="QRCODE_REGENERATED",
    )

    pair_generator = Mock()
    pair_generator.generate.return_value = [
        first_pair,
        second_pair,
    ]

    qrcode_comparator = Mock()
    qrcode_comparator.compare.side_effect = [
        first_comparison,
        second_comparison,
    ]

    finding_builder = Mock()
    finding_builder.build.side_effect = [
        [first_finding],
        [second_finding],
    ]

    cross_comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    findings = cross_comparator.compare(
        [
            {
                "document_id": "document-1",
            },
            {
                "document_id": "document-2",
            },
            {
                "document_id": "document-3",
            },
        ]
    )

    assert findings == [
        first_finding,
        second_finding,
    ]

    assert qrcode_comparator.compare.call_args_list == [
        call(
            first_pair.first_qrcode,
            first_pair.second_qrcode,
        ),
        call(
            second_pair.first_qrcode,
            second_pair.second_qrcode,
        ),
    ]

    assert finding_builder.build.call_args_list == [
        call(
            pair=first_pair,
            comparison=first_comparison,
            comparator=(
                "QRCodeFingerprintCrossComparator"
            ),
        ),
        call(
            pair=second_pair,
            comparison=second_comparison,
            comparator=(
                "QRCodeFingerprintCrossComparator"
            ),
        ),
    ]


def test_should_accumulate_multiple_findings_from_same_pair(
) -> None:
    pair = create_pair(
        first_qrcode=object(),
        second_qrcode=object(),
    )

    comparison = object()

    first_finding = create_finding(
        code="QRCODE_FIRST_FINDING",
    )

    second_finding = create_finding(
        code="QRCODE_SECOND_FINDING",
    )

    pair_generator = Mock()
    pair_generator.generate.return_value = [pair]

    qrcode_comparator = Mock()
    qrcode_comparator.compare.return_value = comparison

    finding_builder = Mock()
    finding_builder.build.return_value = [
        first_finding,
        second_finding,
    ]

    cross_comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    findings = cross_comparator.compare(
        [
            {
                "document_id": "document-1",
            },
            {
                "document_id": "document-2",
            },
        ]
    )

    assert findings == [
        first_finding,
        second_finding,
    ]


def test_should_return_empty_list_when_no_pairs_are_generated(
) -> None:
    pair_generator = Mock()
    pair_generator.generate.return_value = []

    qrcode_comparator = Mock()
    finding_builder = Mock()

    cross_comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    findings = cross_comparator.compare([])

    assert findings == []

    qrcode_comparator.compare.assert_not_called()
    finding_builder.build.assert_not_called()


def test_should_continue_when_pair_produces_no_findings(
) -> None:
    first_pair = create_pair(
        first_qrcode=object(),
        second_qrcode=object(),
    )

    second_pair = create_pair(
        first_qrcode=object(),
        second_qrcode=object(),
    )

    pair_generator = Mock()
    pair_generator.generate.return_value = [
        first_pair,
        second_pair,
    ]

    qrcode_comparator = Mock()
    qrcode_comparator.compare.side_effect = [
        object(),
        object(),
    ]

    expected_finding = create_finding(
        code="QRCODE_EXACT_MATCH",
    )

    finding_builder = Mock()
    finding_builder.build.side_effect = [
        [],
        [expected_finding],
    ]

    cross_comparator = QRCodeFingerprintCrossComparator(
        pair_generator=pair_generator,
        qrcode_comparator=qrcode_comparator,
        finding_builder=finding_builder,
    )

    findings = cross_comparator.compare(
        [
            {
                "document_id": "document-1",
            },
            {
                "document_id": "document-2",
            },
            {
                "document_id": "document-3",
            },
        ]
    )

    assert findings == [expected_finding]

    assert qrcode_comparator.compare.call_count == 2
    assert finding_builder.build.call_count == 2