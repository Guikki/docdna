from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.domain.fingerprints.qrcode_fingerprint import (
    QRCodeFingerprint,
)
from app.domain.services.qrcode_fingerprint_pair_generator import (
    QRCodeFingerprintPairGenerator,
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


def create_qrcode(
    *,
    value: str = "https://example.com",
    image_hash: str | None = "0123456789abcdef",
    page_number: int = 1,
) -> QRCodeFingerprint:
    return QRCodeFingerprint(
        location=DocumentLocation(
            page_number=page_number,
            bounding_box=BoundingBox(
                x=0.0,
                y=0.0,
                width=100.0,
                height=100.0,
            ),
        ),
        confidence=ConfidenceScore(
            value=1.0,
        ),
        value=value,
        encoding="utf-8",
        version=1,
        error_correction="M",
        image_hash=image_hash,
        rotation=0.0,
    )


def test_should_return_empty_list_when_analyses_are_empty(
) -> None:
    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[],
    )

    assert pairs == []


def test_should_not_generate_pair_for_single_document(
) -> None:
    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "qrcode_fingerprints": [
                    create_qrcode(),
                ],
            },
        ],
    )

    assert pairs == []


def test_should_generate_pair_between_two_documents(
) -> None:
    first_qrcode = create_qrcode(
        value="first-value",
    )

    second_qrcode = create_qrcode(
        value="second-value",
    )

    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "qrcode_fingerprints": [
                    first_qrcode,
                ],
            },
            {
                "id": "document-2",
                "qrcode_fingerprints": [
                    second_qrcode,
                ],
            },
        ],
    )

    assert len(pairs) == 1

    pair = pairs[0]

    assert pair.first_document_id == "document-1"
    assert pair.second_document_id == "document-2"
    assert pair.first_qrcode is first_qrcode
    assert pair.second_qrcode is second_qrcode


def test_should_generate_cartesian_product_between_qrcodes(
) -> None:
    first_qrcodes = [
        create_qrcode(
            value="first-a",
            image_hash="0000000000000000",
            page_number=1,
        ),
        create_qrcode(
            value="first-b",
            image_hash="0000000000000001",
            page_number=2,
        ),
    ]

    second_qrcodes = [
        create_qrcode(
            value="second-a",
            image_hash="0000000000000002",
            page_number=1,
        ),
        create_qrcode(
            value="second-b",
            image_hash="0000000000000003",
            page_number=2,
        ),
        create_qrcode(
            value="second-c",
            image_hash="0000000000000004",
            page_number=3,
        ),
    ]

    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "qrcode_fingerprints": first_qrcodes,
            },
            {
                "id": "document-2",
                "qrcode_fingerprints": second_qrcodes,
            },
        ],
    )

    assert len(pairs) == 6

    generated_pairs = {
        (
            pair.first_qrcode.value,
            pair.second_qrcode.value,
        )
        for pair in pairs
    }

    assert generated_pairs == {
        ("first-a", "second-a"),
        ("first-a", "second-b"),
        ("first-a", "second-c"),
        ("first-b", "second-a"),
        ("first-b", "second-b"),
        ("first-b", "second-c"),
    }


def test_should_generate_document_combinations_without_reverse_pairs(
) -> None:
    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-a",
                "qrcode_fingerprints": [
                    create_qrcode(
                        value="value-a",
                    ),
                ],
            },
            {
                "id": "document-b",
                "qrcode_fingerprints": [
                    create_qrcode(
                        value="value-b",
                    ),
                ],
            },
            {
                "id": "document-c",
                "qrcode_fingerprints": [
                    create_qrcode(
                        value="value-c",
                    ),
                ],
            },
        ],
    )

    document_pairs = {
        (
            pair.first_document_id,
            pair.second_document_id,
        )
        for pair in pairs
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


def test_should_ignore_analyses_without_valid_document_id(
) -> None:
    generator = QRCodeFingerprintPairGenerator()

    analyses: list[Any] = [
        {
            "id": "",
            "qrcode_fingerprints": [
                create_qrcode(),
            ],
        },
        {
            "id": "   ",
            "qrcode_fingerprints": [
                create_qrcode(),
            ],
        },
        {
            "qrcode_fingerprints": [
                create_qrcode(),
            ],
        },
        {
            "id": "document-1",
            "qrcode_fingerprints": [
                create_qrcode(),
            ],
        },
        {
            "id": "document-2",
            "qrcode_fingerprints": [
                create_qrcode(),
            ],
        },
    ]

    pairs = generator.generate(
        analyses=analyses,
    )

    assert len(pairs) == 1
    assert pairs[0].first_document_id == "document-1"
    assert pairs[0].second_document_id == "document-2"


def test_should_ignore_analyses_without_qrcode_fingerprints(
) -> None:
    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-without-qrcodes",
                "qrcode_fingerprints": [],
            },
            {
                "id": "document-1",
                "qrcode_fingerprints": [
                    create_qrcode(),
                ],
            },
            {
                "id": "document-2",
                "qrcode_fingerprints": [
                    create_qrcode(),
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


def test_should_ignore_objects_that_are_not_qrcode_fingerprints(
) -> None:
    first_qrcode = create_qrcode(
        value="first",
    )

    second_qrcode = create_qrcode(
        value="second",
    )

    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "qrcode_fingerprints": [
                    object(),
                    "invalid",
                    first_qrcode,
                ],
            },
            {
                "id": "document-2",
                "qrcode_fingerprints": [
                    123,
                    None,
                    second_qrcode,
                ],
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_qrcode is first_qrcode
    assert pairs[0].second_qrcode is second_qrcode


def test_should_ignore_invalid_fingerprint_collection(
) -> None:
    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "qrcode_fingerprints": "not-a-list",
            },
            {
                "id": "document-2",
                "qrcode_fingerprints": [
                    create_qrcode(),
                ],
            },
        ],
    )

    assert pairs == []


def test_should_accept_document_id_fallback(
) -> None:
    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "document_id": "document-1",
                "qrcode_fingerprints": [
                    create_qrcode(),
                ],
            },
            {
                "document_id": "document-2",
                "qrcode_fingerprints": [
                    create_qrcode(),
                ],
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_document_id == "document-1"
    assert pairs[0].second_document_id == "document-2"


def test_should_trim_document_ids(
) -> None:
    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": " document-1 ",
                "qrcode_fingerprints": [
                    create_qrcode(),
                ],
            },
            {
                "id": " document-2 ",
                "qrcode_fingerprints": [
                    create_qrcode(),
                ],
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_document_id == "document-1"
    assert pairs[0].second_document_id == "document-2"


def test_should_accept_uuid_document_ids(
) -> None:
    first_document_id = uuid4()
    second_document_id = uuid4()

    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": first_document_id,
                "qrcode_fingerprints": [
                    create_qrcode(),
                ],
            },
            {
                "id": second_document_id,
                "qrcode_fingerprints": [
                    create_qrcode(),
                ],
            },
        ],
    )

    assert len(pairs) == 1

    assert (
        pairs[0].first_document_id
        == str(first_document_id)
    )

    assert (
        pairs[0].second_document_id
        == str(second_document_id)
    )


def test_should_ignore_duplicate_document_ids(
) -> None:
    first_qrcode = create_qrcode(
        value="first-occurrence",
    )

    duplicate_qrcode = create_qrcode(
        value="duplicate-occurrence",
    )

    second_document_qrcode = create_qrcode(
        value="second-document",
    )

    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "qrcode_fingerprints": [
                    first_qrcode,
                ],
            },
            {
                "id": "document-1",
                "qrcode_fingerprints": [
                    duplicate_qrcode,
                ],
            },
            {
                "id": "document-2",
                "qrcode_fingerprints": [
                    second_document_qrcode,
                ],
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_qrcode is first_qrcode
    assert (
        pairs[0].second_qrcode
        is second_document_qrcode
    )


def test_should_accept_tuple_of_qrcode_fingerprints(
) -> None:
    first_qrcode = create_qrcode(
        value="first",
    )

    second_qrcode = create_qrcode(
        value="second",
    )

    generator = QRCodeFingerprintPairGenerator()

    pairs = generator.generate(
        analyses=[
            {
                "id": "document-1",
                "qrcode_fingerprints": (
                    first_qrcode,
                ),
            },
            {
                "id": "document-2",
                "qrcode_fingerprints": (
                    second_qrcode,
                ),
            },
        ],
    )

    assert len(pairs) == 1
    assert pairs[0].first_qrcode is first_qrcode
    assert pairs[0].second_qrcode is second_qrcode