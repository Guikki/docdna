from __future__ import annotations

from typing import Any
from unittest.mock import Mock

from app.domain.comparators.base_comparator import (
    BaseComparator,
)
from app.domain.comparators.logo_fingerprint_comparator import (
    LogoFingerprintComparator,
)
from app.domain.comparators.logo_fingerprint_cross_comparator import (
    LogoFingerprintCrossComparator,
)
from app.domain.fingerprints.logo_fingerprint import (
    LogoFingerprint,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)
from app.domain.models.logo_fingerprint_comparison import (
    LogoFingerprintComparison,
)
from app.domain.models.logo_fingerprint_pair import (
    LogoFingerprintPair,
)
from app.domain.services.logo_fingerprint_finding_builder import (
    LogoFingerprintFindingBuilder,
)
from app.domain.services.logo_fingerprint_pair_generator import (
    LogoFingerprintPairGenerator,
)


def create_pair(
    *,
    first_document_id: str = "document-1",
    second_document_id: str = "document-2",
) -> LogoFingerprintPair:
    first_logo = Mock(
        spec=LogoFingerprint
    )

    second_logo = Mock(
        spec=LogoFingerprint
    )

    return LogoFingerprintPair(
        first_document_id=first_document_id,
        second_document_id=second_document_id,
        first_logo=first_logo,
        second_logo=second_logo,
    )


def create_comparison(
    *,
    similarity: float = 0.98,
    same_company_name: bool | None = True,
) -> LogoFingerprintComparison:
    return LogoFingerprintComparison(
        exact_image_match=False,
        perceptual_distance=1,
        perceptual_similarity=similarity,
        average_distance=None,
        average_similarity=None,
        difference_distance=None,
        difference_similarity=None,
        same_dimensions=True,
        width_difference=0,
        height_difference=0,
        same_company_name=same_company_name,
    )


def create_finding(
    *,
    code: str = "LOGO_STRONG_VISUAL_MATCH",
    first_document_id: str = "document-1",
    second_document_id: str = "document-2",
) -> CrossValidationFinding:
    return CrossValidationFinding(
        code=code,
        title="Finding de teste",
        description="Descrição do finding de teste.",
        severity=CrossValidationSeverity.MEDIUM,
        confidence=0.98,
        comparator="LogoFingerprintCrossComparator",
        document_ids=[
            first_document_id,
            second_document_id,
        ],
        metadata={},
    )


def test_should_implement_base_comparator() -> None:
    comparator = LogoFingerprintCrossComparator()

    assert isinstance(
        comparator,
        BaseComparator,
    )


def test_should_create_default_dependencies() -> None:
    comparator = LogoFingerprintCrossComparator()

    assert isinstance(
        comparator._pair_generator,
        LogoFingerprintPairGenerator,
    )

    assert isinstance(
        comparator._logo_comparator,
        LogoFingerprintComparator,
    )

    assert isinstance(
        comparator._finding_builder,
        LogoFingerprintFindingBuilder,
    )


def test_should_send_analyses_to_pair_generator() -> None:
    analyses: list[dict[str, Any]] = [
        {
            "id": "document-1",
            "logo_fingerprints": [],
        },
        {
            "id": "document-2",
            "logo_fingerprints": [],
        },
    ]

    pair_generator = Mock(
        spec=LogoFingerprintPairGenerator
    )

    pair_generator.generate.return_value = []

    logo_comparator = Mock(
        spec=LogoFingerprintComparator
    )

    finding_builder = Mock(
        spec=LogoFingerprintFindingBuilder
    )

    comparator = LogoFingerprintCrossComparator(
        pair_generator=pair_generator,
        logo_comparator=logo_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare(analyses)

    pair_generator.generate.assert_called_once_with(
        analyses
    )

    assert result == []


def test_should_not_compare_logos_when_no_pairs_exist() -> None:
    pair_generator = Mock(
        spec=LogoFingerprintPairGenerator
    )

    pair_generator.generate.return_value = []

    logo_comparator = Mock(
        spec=LogoFingerprintComparator
    )

    finding_builder = Mock(
        spec=LogoFingerprintFindingBuilder
    )

    comparator = LogoFingerprintCrossComparator(
        pair_generator=pair_generator,
        logo_comparator=logo_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    logo_comparator.compare.assert_not_called()
    finding_builder.build.assert_not_called()

    assert result == []


def test_should_compare_logos_from_generated_pair() -> None:
    pair = create_pair()
    comparison = create_comparison()

    pair_generator = Mock(
        spec=LogoFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        pair
    ]

    logo_comparator = Mock(
        spec=LogoFingerprintComparator
    )

    logo_comparator.compare.return_value = (
        comparison
    )

    finding_builder = Mock(
        spec=LogoFingerprintFindingBuilder
    )

    finding_builder.build.return_value = []

    comparator = LogoFingerprintCrossComparator(
        pair_generator=pair_generator,
        logo_comparator=logo_comparator,
        finding_builder=finding_builder,
    )

    comparator.compare([])

    logo_comparator.compare.assert_called_once_with(
        pair.first_logo,
        pair.second_logo,
    )


def test_should_send_comparison_to_finding_builder() -> None:
    pair = create_pair()
    comparison = create_comparison()

    pair_generator = Mock(
        spec=LogoFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        pair
    ]

    logo_comparator = Mock(
        spec=LogoFingerprintComparator
    )

    logo_comparator.compare.return_value = (
        comparison
    )

    finding_builder = Mock(
        spec=LogoFingerprintFindingBuilder
    )

    finding_builder.build.return_value = []

    comparator = LogoFingerprintCrossComparator(
        pair_generator=pair_generator,
        logo_comparator=logo_comparator,
        finding_builder=finding_builder,
    )

    comparator.compare([])

    finding_builder.build.assert_called_once_with(
        pair=pair,
        comparison=comparison,
        comparator=(
            "LogoFingerprintCrossComparator"
        ),
    )


def test_should_return_findings_created_by_builder() -> None:
    pair = create_pair()
    comparison = create_comparison()
    finding = create_finding()

    pair_generator = Mock(
        spec=LogoFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        pair
    ]

    logo_comparator = Mock(
        spec=LogoFingerprintComparator
    )

    logo_comparator.compare.return_value = (
        comparison
    )

    finding_builder = Mock(
        spec=LogoFingerprintFindingBuilder
    )

    finding_builder.build.return_value = [
        finding
    ]

    comparator = LogoFingerprintCrossComparator(
        pair_generator=pair_generator,
        logo_comparator=logo_comparator,
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
        similarity=0.98,
    )

    second_comparison = create_comparison(
        similarity=0.96,
    )

    first_finding = create_finding(
        code="LOGO_STRONG_VISUAL_MATCH",
        first_document_id="document-1",
        second_document_id="document-2",
    )

    second_finding = create_finding(
        code="LOGO_VISUAL_MATCH",
        first_document_id="document-1",
        second_document_id="document-3",
    )

    pair_generator = Mock(
        spec=LogoFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        first_pair,
        second_pair,
    ]

    logo_comparator = Mock(
        spec=LogoFingerprintComparator
    )

    logo_comparator.compare.side_effect = [
        first_comparison,
        second_comparison,
    ]

    finding_builder = Mock(
        spec=LogoFingerprintFindingBuilder
    )

    finding_builder.build.side_effect = [
        [first_finding],
        [second_finding],
    ]

    comparator = LogoFingerprintCrossComparator(
        pair_generator=pair_generator,
        logo_comparator=logo_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    assert result == [
        first_finding,
        second_finding,
    ]

    assert logo_comparator.compare.call_count == 2
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
        similarity=0.98,
    )

    second_comparison = create_comparison(
        similarity=0.50,
    )

    finding = create_finding()

    pair_generator = Mock(
        spec=LogoFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        first_pair,
        second_pair,
    ]

    logo_comparator = Mock(
        spec=LogoFingerprintComparator
    )

    logo_comparator.compare.side_effect = [
        first_comparison,
        second_comparison,
    ]

    finding_builder = Mock(
        spec=LogoFingerprintFindingBuilder
    )

    finding_builder.build.side_effect = [
        [finding],
        [],
    ]

    comparator = LogoFingerprintCrossComparator(
        pair_generator=pair_generator,
        logo_comparator=logo_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    assert result == [
        finding
    ]