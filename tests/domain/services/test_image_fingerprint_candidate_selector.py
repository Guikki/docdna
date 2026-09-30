from __future__ import annotations

from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.services.image_fingerprint_candidate_selector import (
    ImageFingerprintCandidateSelector,
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


def create_fingerprint(
    *,
    perceptual_hash: str,
    image_hash: str | None = None,
) -> ImageFingerprint:
    return ImageFingerprint(
        location=DocumentLocation(
            page_number=1,
            bounding_box=BoundingBox(
                x=0.0,
                y=0.0,
                width=640.0,
                height=480.0,
            ),
        ),
        confidence=ConfidenceScore(
            1.0
        ),
        perceptual_hash=(
            perceptual_hash
        ),
        average_hash=(
            perceptual_hash
        ),
        difference_hash=(
            perceptual_hash
        ),
        image_hash=image_hash,
        width=640,
        height=480,
        mime_type="image/png",
    )


def test_empty_input_should_return_empty_selection() -> None:
    result = (
        ImageFingerprintCandidateSelector()
        .select([])
    )

    assert result.pairs == ()

    assert (
        result.stats.documents_total
        == 0
    )

    assert (
        result.stats.fingerprints_total
        == 0
    )

    assert (
        result.stats
        .potential_cross_document_pairs
        == 0
    )

    assert (
        result.stats.candidate_pairs
        == 0
    )


def test_far_perceptual_hashes_should_not_be_candidates(
) -> None:
    first = create_fingerprint(
        perceptual_hash=(
            "0000000000000000"
        ),
    )

    second = create_fingerprint(
        perceptual_hash=(
            "ffffffffffffffff"
        ),
    )

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        first
                    ],
                },
                {
                    "id": "document-2",
                    "image_fingerprints": [
                        second
                    ],
                },
            ]
        )
    )

    assert result.pairs == ()

    assert (
        result.stats
        .potential_cross_document_pairs
        == 1
    )

    assert (
        result.stats.candidate_pairs
        == 0
    )

    assert (
        result.stats.reduction_ratio
        == 1.0
    )


def test_distance_three_should_be_candidate_at_current_threshold(
) -> None:
    first = create_fingerprint(
        perceptual_hash=(
            "0000000000000000"
        ),
    )

    second = create_fingerprint(
        perceptual_hash=(
            "0000000000000007"
        ),
    )

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        first
                    ],
                },
                {
                    "id": "document-2",
                    "image_fingerprints": [
                        second
                    ],
                },
            ]
        )
    )

    assert len(
        result.pairs
    ) == 1

    assert (
        result.pairs[0].first_image
        is first
    )

    assert (
        result.pairs[0].second_image
        is second
    )

    assert (
        result.stats
        .perceptual_only_pairs
        == 1
    )


def test_distance_four_should_not_be_candidate_at_current_threshold(
) -> None:
    first = create_fingerprint(
        perceptual_hash=(
            "0000000000000000"
        ),
    )

    second = create_fingerprint(
        perceptual_hash=(
            "000000000000000f"
        ),
    )

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        first
                    ],
                },
                {
                    "id": "document-2",
                    "image_fingerprints": [
                        second
                    ],
                },
            ]
        )
    )

    assert result.pairs == ()


def test_exact_sha256_should_be_candidate_even_when_phash_is_far(
) -> None:
    shared_sha = (
        "a" * 64
    )

    first = create_fingerprint(
        perceptual_hash=(
            "0000000000000000"
        ),
        image_hash=shared_sha,
    )

    second = create_fingerprint(
        perceptual_hash=(
            "ffffffffffffffff"
        ),
        image_hash=shared_sha,
    )

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        first
                    ],
                },
                {
                    "id": "document-2",
                    "image_fingerprints": [
                        second
                    ],
                },
            ]
        )
    )

    assert len(
        result.pairs
    ) == 1

    assert (
        result.stats
        .exact_sha256_pairs
        == 1
    )

    assert (
        result.stats
        .perceptual_only_pairs
        == 0
    )


def test_same_document_should_never_generate_candidate_pair(
) -> None:
    analyses = [
        {
            "id": "document-1",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash=(
                        "0000000000000000"
                    ),
                ),
                create_fingerprint(
                    perceptual_hash=(
                        "0000000000000001"
                    ),
                ),
            ],
        }
    ]

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            analyses
        )
    )

    assert result.pairs == ()

    assert (
        result.stats
        .potential_cross_document_pairs
        == 0
    )


def test_candidate_matching_multiple_segments_should_appear_once(
) -> None:
    first = create_fingerprint(
        perceptual_hash=(
            "0000000000000000"
        ),
    )

    second = create_fingerprint(
        perceptual_hash=(
            "0000000000000001"
        ),
    )

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        first
                    ],
                },
                {
                    "id": "document-2",
                    "image_fingerprints": [
                        second
                    ],
                },
            ]
        )
    )

    assert len(
        result.pairs
    ) == 1

    assert (
        result.stats.candidate_pairs
        == 1
    )


def test_should_calculate_cartesian_space_without_materializing_it(
) -> None:
    first_document = [
        create_fingerprint(
            perceptual_hash=(
                f"{value:016x}"
            ),
        )
        for value in range(
            2
        )
    ]

    second_document = [
        create_fingerprint(
            perceptual_hash=(
                f"{value + 1000:016x}"
            ),
        )
        for value in range(
            3
        )
    ]

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": (
                        first_document
                    ),
                },
                {
                    "id": "document-2",
                    "image_fingerprints": (
                        second_document
                    ),
                },
            ]
        )
    )

    assert (
        result.stats
        .potential_cross_document_pairs
        == 6
    )

    assert (
        result.stats.fingerprints_total
        == 5
    )


def test_should_process_only_first_analysis_for_duplicate_document_id(
) -> None:
    first = create_fingerprint(
        perceptual_hash=(
            "0000000000000000"
        ),
    )

    duplicated = create_fingerprint(
        perceptual_hash=(
            "ffffffffffffffff"
        ),
    )

    second = create_fingerprint(
        perceptual_hash=(
            "0000000000000001"
        ),
    )

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        first
                    ],
                },
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        duplicated
                    ],
                },
                {
                    "id": "document-2",
                    "image_fingerprints": [
                        second
                    ],
                },
            ]
        )
    )

    assert len(
        result.pairs
    ) == 1

    assert (
        result.pairs[0].first_image
        is first
    )


def test_should_support_different_valid_hash_lengths(
) -> None:
    first = create_fingerprint(
        perceptual_hash=(
            "00000000"
        ),
    )

    second = create_fingerprint(
        perceptual_hash=(
            "00000001"
        ),
    )

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        first
                    ],
                },
                {
                    "id": "document-2",
                    "image_fingerprints": [
                        second
                    ],
                },
            ]
        )
    )

    assert len(
        result.pairs
    ) == 1


def test_incompatible_hash_lengths_should_not_be_visual_candidates(
) -> None:
    first = create_fingerprint(
        perceptual_hash=(
            "00000000"
        ),
    )

    second = create_fingerprint(
        perceptual_hash=(
            "0000000000000000"
        ),
    )

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        first
                    ],
                },
                {
                    "id": "document-2",
                    "image_fingerprints": [
                        second
                    ],
                },
            ]
        )
    )

    assert result.pairs == ()


def test_invalid_perceptual_hash_should_fail_explicitly(
) -> None:
    invalid = create_fingerprint(
        perceptual_hash=(
            "not-a-hash"
        ),
    )

    try:
        (
            ImageFingerprintCandidateSelector()
            .select(
                [
                    {
                        "id": "document-1",
                        "image_fingerprints": [
                            invalid
                        ],
                    }
                ]
            )
        )
    except ValueError as error:
        assert (
            "perceptual_hash"
            in str(error)
        )
    else:
        raise AssertionError(
            "Era esperado ValueError "
            "para pHash inválido."
        )


def test_exact_and_perceptual_match_should_not_duplicate_pair(
) -> None:
    shared_sha = (
        "b" * 64
    )

    first = create_fingerprint(
        perceptual_hash=(
            "0000000000000000"
        ),
        image_hash=shared_sha,
    )

    second = create_fingerprint(
        perceptual_hash=(
            "0000000000000001"
        ),
        image_hash=shared_sha,
    )

    result = (
        ImageFingerprintCandidateSelector()
        .select(
            [
                {
                    "id": "document-1",
                    "image_fingerprints": [
                        first
                    ],
                },
                {
                    "id": "document-2",
                    "image_fingerprints": [
                        second
                    ],
                },
            ]
        )
    )

    assert len(
        result.pairs
    ) == 1

    assert (
        result.stats
        .exact_sha256_pairs
        == 1
    )

    assert (
        result.stats
        .perceptual_only_pairs
        == 0
    )