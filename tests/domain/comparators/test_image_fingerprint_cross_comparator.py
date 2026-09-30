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
from app.domain.models.image_fingerprint_candidate_selection import (
    ImageFingerprintCandidateSelectionResult,
    ImageFingerprintCandidateSelectionStats,
)
from app.domain.models.image_fingerprint_comparison import (
    ImageFingerprintComparison,
)
from app.domain.models.image_fingerprint_pair import (
    ImageFingerprintPair,
)
from app.domain.services.image_fingerprint_candidate_selector import (
    ImageFingerprintCandidateSelector,
)
from app.domain.services.image_fingerprint_finding_builder import (
    ImageFingerprintFindingBuilder,
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
        first_document_id=(
            first_document_id
        ),
        second_document_id=(
            second_document_id
        ),
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
        perceptual_similarity=(
            similarity
        ),
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
    code: str = (
        "IMAGE_STRONG_VISUAL_MATCH"
    ),
    first_document_id: str = (
        "document-1"
    ),
    second_document_id: str = (
        "document-2"
    ),
) -> CrossValidationFinding:
    return CrossValidationFinding(
        code=code,
        title="Finding de teste",
        description=(
            "Descrição do finding de teste."
        ),
        severity=(
            CrossValidationSeverity.MEDIUM
        ),
        confidence=0.98,
        comparator=(
            "ImageFingerprintCrossComparator"
        ),
        document_ids=[
            first_document_id,
            second_document_id,
        ],
        metadata={},
    )


def create_stats(
    *,
    candidate_pairs: int = 0,
) -> (
    ImageFingerprintCandidateSelectionStats
):
    return (
        ImageFingerprintCandidateSelectionStats(
            documents_total=2,
            fingerprints_total=2,
            potential_cross_document_pairs=1,
            candidate_pairs=(
                candidate_pairs
            ),
            exact_sha256_pairs=0,
            perceptual_only_pairs=(
                candidate_pairs
            ),
            reduction_ratio=(
                0.0
                if candidate_pairs
                else 1.0
            ),
        )
    )


def create_selection(
    *pairs: ImageFingerprintPair,
) -> ImageFingerprintCandidateSelectionResult:
    return (
        ImageFingerprintCandidateSelectionResult(
            pairs=tuple(
                pairs
            ),
            stats=create_stats(
                candidate_pairs=len(
                    pairs
                )
            ),
        )
    )


def test_should_implement_base_comparator(
) -> None:
    comparator = (
        ImageFingerprintCrossComparator()
    )

    assert isinstance(
        comparator,
        BaseComparator,
    )


def test_should_create_default_dependencies(
) -> None:
    comparator = (
        ImageFingerprintCrossComparator()
    )

    assert isinstance(
        comparator._candidate_selector,
        ImageFingerprintCandidateSelector,
    )

    assert isinstance(
        comparator._image_comparator,
        ImageFingerprintComparator,
    )

    assert isinstance(
        comparator._finding_builder,
        ImageFingerprintFindingBuilder,
    )


def test_should_not_use_legacy_pair_generator(
) -> None:
    comparator = (
        ImageFingerprintCrossComparator()
    )

    assert not hasattr(
        comparator,
        "_pair_generator",
    )


def test_should_send_analyses_to_candidate_selector(
) -> None:
    analyses: list[
        dict[str, Any]
    ] = [
        {
            "id": "document-1",
            "image_fingerprints": [],
        },
        {
            "id": "document-2",
            "image_fingerprints": [],
        },
    ]

    candidate_selector = Mock(
        spec=(
            ImageFingerprintCandidateSelector
        )
    )

    candidate_selector.select.return_value = (
        create_selection()
    )

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    comparator = (
        ImageFingerprintCrossComparator(
            candidate_selector=(
                candidate_selector
            ),
            image_comparator=(
                image_comparator
            ),
            finding_builder=(
                finding_builder
            ),
        )
    )

    result = comparator.compare(
        analyses
    )

    (
        candidate_selector
        .select
        .assert_called_once_with(
            analyses
        )
    )

    assert result == []


def test_should_expose_selection_stats(
) -> None:
    candidate_selector = Mock(
        spec=(
            ImageFingerprintCandidateSelector
        )
    )

    selection = (
        create_selection()
    )

    candidate_selector.select.return_value = (
        selection
    )

    comparator = (
        ImageFingerprintCrossComparator(
            candidate_selector=(
                candidate_selector
            ),
        )
    )

    assert (
        comparator.selection_stats
        is None
    )

    comparator.compare([])

    assert (
        comparator.selection_stats
        is selection.stats
    )


def test_should_not_compare_images_when_no_candidates_exist(
) -> None:
    candidate_selector = Mock(
        spec=(
            ImageFingerprintCandidateSelector
        )
    )

    candidate_selector.select.return_value = (
        create_selection()
    )

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    comparator = (
        ImageFingerprintCrossComparator(
            candidate_selector=(
                candidate_selector
            ),
            image_comparator=(
                image_comparator
            ),
            finding_builder=(
                finding_builder
            ),
        )
    )

    result = comparator.compare([])

    (
        image_comparator
        .compare
        .assert_not_called()
    )

    (
        finding_builder
        .build
        .assert_not_called()
    )

    assert result == []


def test_should_compare_images_from_selected_candidate(
) -> None:
    pair = create_pair()

    comparison = (
        create_comparison()
    )

    candidate_selector = Mock(
        spec=(
            ImageFingerprintCandidateSelector
        )
    )

    candidate_selector.select.return_value = (
        create_selection(
            pair
        )
    )

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

    comparator = (
        ImageFingerprintCrossComparator(
            candidate_selector=(
                candidate_selector
            ),
            image_comparator=(
                image_comparator
            ),
            finding_builder=(
                finding_builder
            ),
        )
    )

    comparator.compare([])

    (
        image_comparator
        .compare
        .assert_called_once_with(
            pair.first_image,
            pair.second_image,
        )
    )


def test_should_send_comparison_to_finding_builder(
) -> None:
    pair = create_pair()

    comparison = (
        create_comparison()
    )

    candidate_selector = Mock(
        spec=(
            ImageFingerprintCandidateSelector
        )
    )

    candidate_selector.select.return_value = (
        create_selection(
            pair
        )
    )

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

    comparator = (
        ImageFingerprintCrossComparator(
            candidate_selector=(
                candidate_selector
            ),
            image_comparator=(
                image_comparator
            ),
            finding_builder=(
                finding_builder
            ),
        )
    )

    comparator.compare([])

    (
        finding_builder
        .build
        .assert_called_once_with(
            pair=pair,
            comparison=comparison,
            comparator=(
                "ImageFingerprintCrossComparator"
            ),
        )
    )


def test_should_return_findings_created_by_builder(
) -> None:
    pair = create_pair()

    comparison = (
        create_comparison()
    )

    finding = (
        create_finding()
    )

    candidate_selector = Mock(
        spec=(
            ImageFingerprintCandidateSelector
        )
    )

    candidate_selector.select.return_value = (
        create_selection(
            pair
        )
    )

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

    comparator = (
        ImageFingerprintCrossComparator(
            candidate_selector=(
                candidate_selector
            ),
            image_comparator=(
                image_comparator
            ),
            finding_builder=(
                finding_builder
            ),
        )
    )

    result = comparator.compare([])

    assert result == [
        finding
    ]


def test_should_aggregate_findings_from_multiple_candidates(
) -> None:
    first_pair = create_pair(
        first_document_id="document-1",
        second_document_id="document-2",
    )

    second_pair = create_pair(
        first_document_id="document-1",
        second_document_id="document-3",
    )

    first_comparison = (
        create_comparison(
            similarity=0.98,
        )
    )

    second_comparison = (
        create_comparison(
            similarity=0.96,
        )
    )

    first_finding = create_finding(
        code=(
            "IMAGE_STRONG_VISUAL_MATCH"
        ),
        first_document_id="document-1",
        second_document_id="document-2",
    )

    second_finding = create_finding(
        code="IMAGE_VISUAL_MATCH",
        first_document_id="document-1",
        second_document_id="document-3",
    )

    candidate_selector = Mock(
        spec=(
            ImageFingerprintCandidateSelector
        )
    )

    candidate_selector.select.return_value = (
        create_selection(
            first_pair,
            second_pair,
        )
    )

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

    comparator = (
        ImageFingerprintCrossComparator(
            candidate_selector=(
                candidate_selector
            ),
            image_comparator=(
                image_comparator
            ),
            finding_builder=(
                finding_builder
            ),
        )
    )

    result = comparator.compare([])

    assert result == [
        first_finding,
        second_finding,
    ]

    assert (
        image_comparator
        .compare
        .call_count
        == 2
    )

    assert (
        finding_builder
        .build
        .call_count
        == 2
    )


def test_should_ignore_candidate_when_builder_returns_no_finding(
) -> None:
    first_pair = create_pair(
        first_document_id="document-1",
        second_document_id="document-2",
    )

    second_pair = create_pair(
        first_document_id="document-1",
        second_document_id="document-3",
    )

    first_comparison = (
        create_comparison(
            similarity=0.98,
        )
    )

    second_comparison = (
        create_comparison(
            similarity=0.95,
        )
    )

    finding = create_finding()

    candidate_selector = Mock(
        spec=(
            ImageFingerprintCandidateSelector
        )
    )

    candidate_selector.select.return_value = (
        create_selection(
            first_pair,
            second_pair,
        )
    )

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

    comparator = (
        ImageFingerprintCrossComparator(
            candidate_selector=(
                candidate_selector
            ),
            image_comparator=(
                image_comparator
            ),
            finding_builder=(
                finding_builder
            ),
        )
    )

    result = comparator.compare([])

    assert result == [
        finding
    ]


def test_selection_stats_should_be_replaced_on_each_execution(
) -> None:
    candidate_selector = Mock(
        spec=(
            ImageFingerprintCandidateSelector
        )
    )

    first_selection = (
        ImageFingerprintCandidateSelectionResult(
            pairs=(),
            stats=(
                ImageFingerprintCandidateSelectionStats(
                    documents_total=2,
                    fingerprints_total=10,
                    potential_cross_document_pairs=25,
                    candidate_pairs=0,
                    exact_sha256_pairs=0,
                    perceptual_only_pairs=0,
                    reduction_ratio=1.0,
                )
            ),
        )
    )

    pair = create_pair()

    second_selection = (
        ImageFingerprintCandidateSelectionResult(
            pairs=(
                pair,
            ),
            stats=(
                ImageFingerprintCandidateSelectionStats(
                    documents_total=2,
                    fingerprints_total=10,
                    potential_cross_document_pairs=25,
                    candidate_pairs=1,
                    exact_sha256_pairs=0,
                    perceptual_only_pairs=1,
                    reduction_ratio=0.96,
                )
            ),
        )
    )

    candidate_selector.select.side_effect = [
        first_selection,
        second_selection,
    ]

    image_comparator = Mock(
        spec=ImageFingerprintComparator
    )

    image_comparator.compare.return_value = (
        create_comparison()
    )

    finding_builder = Mock(
        spec=ImageFingerprintFindingBuilder
    )

    finding_builder.build.return_value = []

    comparator = (
        ImageFingerprintCrossComparator(
            candidate_selector=(
                candidate_selector
            ),
            image_comparator=(
                image_comparator
            ),
            finding_builder=(
                finding_builder
            ),
        )
    )

    comparator.compare([])

    assert (
        comparator
        .selection_stats
        .candidate_pairs
        == 0
    )

    comparator.compare([])

    assert (
        comparator
        .selection_stats
        .candidate_pairs
        == 1
    )

    assert (
        comparator
        .selection_stats
        .reduction_ratio
        == 0.96
    )