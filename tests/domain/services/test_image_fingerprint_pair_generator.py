from __future__ import annotations

from uuid import uuid4

from app.domain.fingerprints.image_fingerprint import (
    ImageFingerprint,
)
from app.domain.services.image_fingerprint_pair_generator import (
    ImageFingerprintPairGenerator,
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
    perceptual_hash: str,
    page_number: int = 1,
) -> ImageFingerprint:
    return ImageFingerprint(
        location=DocumentLocation(
            page_number=page_number,
            bounding_box=BoundingBox(
                x=0.0,
                y=0.0,
                width=640.0,
                height=480.0,
            ),
        ),
        confidence=ConfidenceScore(1.0),
        perceptual_hash=perceptual_hash,
        average_hash=perceptual_hash,
        difference_hash=perceptual_hash,
        image_hash=perceptual_hash * 4,
        width=640,
        height=480,
        mime_type="image/png",
    )


def test_should_generate_pairs_between_two_documents() -> None:
    first_image = create_fingerprint(
        perceptual_hash="0000000000000000",
    )

    second_image = create_fingerprint(
        perceptual_hash="0000000000000001",
    )

    analyses = [
        {
            "id": "document-1",
            "image_fingerprints": [first_image],
        },
        {
            "id": "document-2",
            "image_fingerprints": [second_image],
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert len(result) == 1

    pair = result[0]

    assert pair.first_document_id == "document-1"
    assert pair.second_document_id == "document-2"
    assert pair.first_image is first_image
    assert pair.second_image is second_image


def test_should_generate_cartesian_product_between_images() -> None:
    first_images = [
        create_fingerprint(
            perceptual_hash="0000000000000000",
            page_number=1,
        ),
        create_fingerprint(
            perceptual_hash="0000000000000001",
            page_number=2,
        ),
    ]

    second_images = [
        create_fingerprint(
            perceptual_hash="0000000000000002",
            page_number=1,
        ),
        create_fingerprint(
            perceptual_hash="0000000000000003",
            page_number=2,
        ),
        create_fingerprint(
            perceptual_hash="0000000000000004",
            page_number=3,
        ),
    ]

    analyses = [
        {
            "id": "document-1",
            "image_fingerprints": first_images,
        },
        {
            "id": "document-2",
            "image_fingerprints": second_images,
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert len(result) == 6

    generated_pairs = {
        (
            pair.first_image.perceptual_hash,
            pair.second_image.perceptual_hash,
        )
        for pair in result
    }

    assert generated_pairs == {
        (
            "0000000000000000",
            "0000000000000002",
        ),
        (
            "0000000000000000",
            "0000000000000003",
        ),
        (
            "0000000000000000",
            "0000000000000004",
        ),
        (
            "0000000000000001",
            "0000000000000002",
        ),
        (
            "0000000000000001",
            "0000000000000003",
        ),
        (
            "0000000000000001",
            "0000000000000004",
        ),
    }


def test_should_generate_document_combinations_without_reverse_pairs(
) -> None:
    analyses = [
        {
            "id": "document-a",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="000000000000000a",
                )
            ],
        },
        {
            "id": "document-b",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="000000000000000b",
                )
            ],
        },
        {
            "id": "document-c",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="000000000000000c",
                )
            ],
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    document_pairs = {
        (
            pair.first_document_id,
            pair.second_document_id,
        )
        for pair in result
    }

    assert document_pairs == {
        ("document-a", "document-b"),
        ("document-a", "document-c"),
        ("document-b", "document-c"),
    }

    assert (
        "document-b",
        "document-a",
    ) not in document_pairs

    assert (
        "document-c",
        "document-a",
    ) not in document_pairs

    assert (
        "document-c",
        "document-b",
    ) not in document_pairs


def test_should_not_generate_pairs_within_same_document() -> None:
    analyses = [
        {
            "id": "document-1",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="0000000000000000",
                ),
                create_fingerprint(
                    perceptual_hash="0000000000000001",
                ),
            ],
        }
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert result == []


def test_should_ignore_analysis_without_document_id() -> None:
    analyses = [
        {
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="0000000000000000",
                )
            ],
        },
        {
            "id": "document-2",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="0000000000000001",
                )
            ],
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert result == []


def test_should_ignore_analysis_without_image_fingerprints() -> None:
    analyses = [
        {
            "id": "document-1",
            "image_fingerprints": [],
        },
        {
            "id": "document-2",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="0000000000000001",
                )
            ],
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert result == []


def test_should_ignore_invalid_fingerprint_objects() -> None:
    valid_first_image = create_fingerprint(
        perceptual_hash="0000000000000000",
    )

    valid_second_image = create_fingerprint(
        perceptual_hash="0000000000000001",
    )

    analyses = [
        {
            "id": "document-1",
            "image_fingerprints": [
                valid_first_image,
                "invalid-fingerprint",
                None,
            ],
        },
        {
            "id": "document-2",
            "image_fingerprints": [
                valid_second_image,
                {"perceptual_hash": "invalid"},
            ],
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert len(result) == 1
    assert result[0].first_image is valid_first_image
    assert result[0].second_image is valid_second_image


def test_should_ignore_invalid_fingerprint_collection() -> None:
    analyses = [
        {
            "id": "document-1",
            "image_fingerprints": "not-a-list",
        },
        {
            "id": "document-2",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="0000000000000001",
                )
            ],
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert result == []


def test_should_accept_document_id_fallback() -> None:
    analyses = [
        {
            "document_id": "document-1",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="0000000000000000",
                )
            ],
        },
        {
            "document_id": "document-2",
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="0000000000000001",
                )
            ],
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert len(result) == 1
    assert result[0].first_document_id == "document-1"
    assert result[0].second_document_id == "document-2"


def test_should_accept_uuid_document_ids() -> None:
    first_document_id = uuid4()
    second_document_id = uuid4()

    analyses = [
        {
            "id": first_document_id,
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="0000000000000000",
                )
            ],
        },
        {
            "id": second_document_id,
            "image_fingerprints": [
                create_fingerprint(
                    perceptual_hash="0000000000000001",
                )
            ],
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert len(result) == 1

    assert (
        result[0].first_document_id
        == str(first_document_id)
    )

    assert (
        result[0].second_document_id
        == str(second_document_id)
    )


def test_should_process_only_first_analysis_for_duplicate_id() -> None:
    first_image = create_fingerprint(
        perceptual_hash="0000000000000000",
    )

    duplicated_image = create_fingerprint(
        perceptual_hash="ffffffffffffffff",
    )

    second_document_image = create_fingerprint(
        perceptual_hash="0000000000000001",
    )

    analyses = [
        {
            "id": "document-1",
            "image_fingerprints": [first_image],
        },
        {
            "id": "document-1",
            "image_fingerprints": [duplicated_image],
        },
        {
            "id": "document-2",
            "image_fingerprints": [
                second_document_image
            ],
        },
    ]

    result = ImageFingerprintPairGenerator().generate(
        analyses
    )

    assert len(result) == 1
    assert result[0].first_image is first_image

    assert all(
        pair.first_image is not duplicated_image
        for pair in result
    )


def test_should_return_empty_list_for_empty_input() -> None:
    result = ImageFingerprintPairGenerator().generate([])

    assert result == []