from __future__ import annotations

from typing import Any
from unittest.mock import Mock

from app.domain.comparators.base_comparator import (
    BaseComparator,
)
from app.domain.comparators.image_fingerprint_comparator import (
    ImageFingerprintComparator,
)
from app.domain.comparators.image_fingerprint_cross_comparator import (
    ImageFingerprintCrossComparator,
)
from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)
from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)
from app.domain.models.image_fingerprint_pair import (
    ImageFingerprintPair,
)
from app.domain.services.image_fingerprint_finding_builder import (
    ImageFingerprintFindingBuilder,
)
from app.domain.services.image_fingerprint_pair_generator import (
    ImageFingerprintPairGenerator,
)


def create_pair(
    *,
    first_document_id: str = "document-1",
    second_document_id: str = "document-2",
) -> ImageFingerprintPair:
    first_image = Mock(
        spec=ImageFingerprint
    )

    second_image = Mock(
        spec=ImageFingerprint
    )

    return ImageFingerprintPair(
        first_document_id=first_document_id,
        second_document_id=second_document_id,
        first_image=first_image,
        second_image=second_image,
    )


def create_comparison(
    *,
    similarity: float = 0.98,
) -> ImageFingerprintComparison:
    return ImageFingerprintComparison(
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
    )


def create_finding(
    *,
    code: str = "IMAGE_STRONG_VISUAL_MATCH",
    first_document_id: str = "document-1",
    second_document_id: str = "document-2",
) -> CrossValidationFinding:
    return CrossValidationFinding(
        code=code,
        title="Finding de teste",
        description="Descrição do finding de teste.",
        severity=CrossValidationSeverity.MEDIUM,
        confidence=0.98,
        comparator="ImageFingerprintCrossComparator",
        document_ids=[
            first_document_id,
            second_document_id,
        ],
        metadata={},
    )


def test_should_implement_base_comparator() -> None:
    comparator = ImageFingerprintCrossComparator()

    assert isinstance(
        comparator,
        BaseComparator,
    )


def test_should_create_default_dependencies() -> None:
    comparator = ImageFingerprintCrossComparator()

    assert isinstance(
        comparator._pair_generator,
        ImageFingerprintPairGenerator,
    )

    assert isinstance(
        comparator._image_comparator,
        ImageFingerprintComparator,
    )

    assert isinstance(
        comparator._finding_builder,
        ImageFingerprintFindingBuilder,
    )


def test_should_send_analyses_to_pair_generator() -> None:
    analyses: list[dict[str, Any]] = [
        {
            "id": "document-1",
            "image_fingerprints": [],
        },
        {
            "id": "document-2",
            "image_fingerprints": [],
        },
    ]

    pair_generator = Mock(
        spec=ImageFingerprintPairGenerator
    )

    pair_generator.generate.return_value = []

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    comparator = ImageFingerprintCrossComparator(
        pair_generator=pair_generator,
        image_comparator=image_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare(analyses)

    pair_generator.generate.assert_called_once_with(
        analyses
    )

    assert result == []


def test_should_not_compare_images_when_no_pairs_exist() -> None:
    pair_generator = Mock(
        spec=ImageFingerprintPairGenerator
    )

    pair_generator.generate.return_value = []

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    comparator = ImageFingerprintCrossComparator(
        pair_generator=pair_generator,
        image_comparator=image_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    image_comparator.compare.assert_not_called()
    finding_builder.build.assert_not_called()

    assert result == []


def test_should_compare_images_from_generated_pair() -> None:
    pair = create_pair()
    comparison = create_comparison()

    pair_generator = Mock(
        spec=ImageFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        pair
    ]

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    image_comparator.compare.return_value = (
        comparison
    )

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    finding_builder.build.return_value = []

    comparator = ImageFingerprintCrossComparator(
        pair_generator=pair_generator,
        image_comparator=image_comparator,
        finding_builder=finding_builder,
    )

    comparator.compare([])

    image_comparator.compare.assert_called_once_with(
        pair.first_image,
        pair.second_image,
    )


def test_should_send_comparison_to_finding_builder() -> None:
    pair = create_pair()
    comparison = create_comparison()

    pair_generator = Mock(
        spec=ImageFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        pair
    ]

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    image_comparator.compare.return_value = (
        comparison
    )

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    finding_builder.build.return_value = []

    comparator = ImageFingerprintCrossComparator(
        pair_generator=pair_generator,
        image_comparator=image_comparator,
        finding_builder=finding_builder,
    )

    comparator.compare([])

    finding_builder.build.assert_called_once_with(
        pair=pair,
        comparison=comparison,
        comparator=(
            "ImageFingerprintCrossComparator"
        ),
    )


def test_should_return_findings_created_by_builder() -> None:
    pair = create_pair()
    comparison = create_comparison()
    finding = create_finding()

    pair_generator = Mock(
        spec=ImageFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        pair
    ]

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    image_comparator.compare.return_value = (
        comparison
    )

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    finding_builder.build.return_value = [
        finding
    ]

    comparator = ImageFingerprintCrossComparator(
        pair_generator=pair_generator,
        image_comparator=image_comparator,
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
        code="IMAGE_STRONG_VISUAL_MATCH",
        first_document_id="document-1",
        second_document_id="document-2",
    )

    second_finding = create_finding(
        code="IMAGE_VISUAL_MATCH",
        first_document_id="document-1",
        second_document_id="document-3",
    )

    pair_generator = Mock(
        spec=ImageFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        first_pair,
        second_pair,
    ]

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    image_comparator.compare.side_effect = [
        first_comparison,
        second_comparison,
    ]

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    finding_builder.build.side_effect = [
        [first_finding],
        [second_finding],
    ]

    comparator = ImageFingerprintCrossComparator(
        pair_generator=pair_generator,
        image_comparator=image_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    assert result == [
        first_finding,
        second_finding,
    ]

    assert image_comparator.compare.call_count == 2
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
        spec=ImageFingerprintPairGenerator
    )

    pair_generator.generate.return_value = [
        first_pair,
        second_pair,
    ]

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    image_comparator.compare.side_effect = [
        first_comparison,
        second_comparison,
    ]

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    finding_builder.build.side_effect = [
        [finding],
        [],
    ]

    comparator = ImageFingerprintCrossComparator(
        pair_generator=pair_generator,
        image_comparator=image_comparator,
        finding_builder=finding_builder,
    )

    result = comparator.compare([])

    assert result == [
        finding
    ]