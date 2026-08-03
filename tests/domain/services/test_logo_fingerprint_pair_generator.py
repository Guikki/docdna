from __future__ import annotations

from typing import Any

from app.domain.fingerprints.logo_fingerprint import (
    LogoFingerprint,
)
from app.domain.services.logo_fingerprint_pair_generator import (
    LogoFingerprintPairGenerator,
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


def create_logo(
    *,
    company_name: str = "OpenAI",
    perceptual_hash: str = "0123456789abcdef",
) -> LogoFingerprint:
    return LogoFingerprint(
        location=DocumentLocation(
            page_number=1,
            bounding_box=BoundingBox(
                x=0,
                y=0,
                width=100,
                height=50,
            ),
        ),
        confidence=ConfidenceScore(
            value=1.0,
        ),
        perceptual_hash=perceptual_hash,
        average_hash="0123456789abcdef",
        difference_hash="0123456789abcdef",
        image_hash="abcdef",
        width=100,
        height=50,
        company_name=company_name,
    )


def test_should_return_empty_list_when_analyses_are_empty(
) -> None:
    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[],
    )

    assert pairs == []


def test_should_not_generate_pair_for_single_document(
) -> None:
    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
        ],
    )

    assert pairs == []


def test_should_generate_pair_between_two_documents(
) -> None:
    first_logo = create_logo(
        company_name="OpenAI",
    )

    second_logo = create_logo(
        company_name="OpenAI",
    )

    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "logo_fingerprints": [
                    first_logo,
                ],
            },
            {
                "id": "document-2",
                "logo_fingerprints": [
                    second_logo,
                ],
            },
        ],
    )

    assert len(pairs) == 1

    pair = pairs[0]

    assert pair.first_document_id == "document-1"
    assert pair.second_document_id == "document-2"
    assert pair.first_logo is first_logo
    assert pair.second_logo is second_logo


def test_should_generate_cartesian_product_between_logos(
) -> None:
    first_logo = create_logo(
        company_name="Company A",
        perceptual_hash="0000000000000000",
    )

    second_logo = create_logo(
        company_name="Company B",
        perceptual_hash="1111111111111111",
    )

    third_logo = create_logo(
        company_name="Company C",
        perceptual_hash="2222222222222222",
    )

    fourth_logo = create_logo(
        company_name="Company D",
        perceptual_hash="3333333333333333",
    )

    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "logo_fingerprints": [
                    first_logo,
                    second_logo,
                ],
            },
            {
                "id": "document-2",
                "logo_fingerprints": [
                    third_logo,
                    fourth_logo,
                ],
            },
        ],
    )

    assert len(pairs) == 4

    generated_pairs = {
        (
            pair.first_logo.company_name,
            pair.second_logo.company_name,
        )
        for pair in pairs
    }

    assert generated_pairs == {
        (
            "Company A",
            "Company C",
        ),
        (
            "Company A",
            "Company D",
        ),
        (
            "Company B",
            "Company C",
        ),
        (
            "Company B",
            "Company D",
        ),
    }


def test_should_not_generate_reverse_pairs(
) -> None:
    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
            {
                "id": "document-2",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
            {
                "id": "document-3",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
        ],
    )

    assert len(pairs) == 3

    document_pairs = [
        (
            pair.first_document_id,
            pair.second_document_id,
        )
        for pair in pairs
    ]

    assert document_pairs == [
        (
            "document-1",
            "document-2",
        ),
        (
            "document-1",
            "document-3",
        ),
        (
            "document-2",
            "document-3",
        ),
    ]


def test_should_accept_document_id_key(
) -> None:
    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "document_id": "document-1",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
            {
                "document_id": "document-2",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_document_id == "document-1"
    assert pairs[0].second_document_id == "document-2"


def test_should_trim_document_ids(
) -> None:
    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": " document-1 ",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
            {
                "id": " document-2 ",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_document_id == "document-1"
    assert pairs[0].second_document_id == "document-2"


def test_should_ignore_analyses_without_valid_document_id(
) -> None:
    generator = LogoFingerprintPairGenerator()

    analyses: list[Any] = [
        {
            "id": "",
            "logo_fingerprints": [
                create_logo(),
            ],
        },
        {
            "id": "   ",
            "logo_fingerprints": [
                create_logo(),
            ],
        },
        {
            "logo_fingerprints": [
                create_logo(),
            ],
        },
        {
            "id": "document-1",
            "logo_fingerprints": [
                create_logo(),
            ],
        },
        {
            "id": "document-2",
            "logo_fingerprints": [
                create_logo(),
            ],
        },
    ]

    pairs = generator.generate(
        analyses=analyses,
    )

    assert len(pairs) == 1
    assert pairs[0].first_document_id == "document-1"
    assert pairs[0].second_document_id == "document-2"


def test_should_ignore_analyses_without_logo_fingerprints(
) -> None:
    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-without-logos",
                "logo_fingerprints": [],
            },
            {
                "id": "document-1",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
            {
                "id": "document-2",
                "logo_fingerprints": [
                    create_logo(),
                ],
            },
        ],
    )

    assert len(pairs) == 1

    assert {
        pairs[0].first_document_id,
        pairs[0].second_document_id,
    } == {
        "document-1",
        "document-2",
    }


def test_should_ignore_objects_that_are_not_logo_fingerprints(
) -> None:
    first_logo = create_logo()
    second_logo = create_logo()

    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "logo_fingerprints": [
                    object(),
                    "invalid",
                    first_logo,
                ],
            },
            {
                "id": "document-2",
                "logo_fingerprints": [
                    123,
                    None,
                    second_logo,
                ],
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_logo is first_logo
    assert pairs[0].second_logo is second_logo


def test_should_ignore_duplicate_document_ids(
) -> None:
    first_logo = create_logo(
        company_name="First occurrence",
    )

    duplicate_logo = create_logo(
        company_name="Duplicate occurrence",
    )

    second_document_logo = create_logo(
        company_name="Second document",
    )

    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "logo_fingerprints": [
                    first_logo,
                ],
            },
            {
                "id": "document-1",
                "logo_fingerprints": [
                    duplicate_logo,
                ],
            },
            {
                "id": "document-2",
                "logo_fingerprints": [
                    second_document_logo,
                ],
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_logo is first_logo
    assert pairs[0].second_logo is second_document_logo


def test_should_accept_tuple_of_logo_fingerprints(
) -> None:
    first_logo = create_logo()
    second_logo = create_logo()

    generator = LogoFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "logo_fingerprints": (
                    first_logo,
                ),
            },
            {
                "id": "document-2",
                "logo_fingerprints": (
                    second_logo,
                ),
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_logo is first_logo
    assert pairs[0].second_logo is second_logo