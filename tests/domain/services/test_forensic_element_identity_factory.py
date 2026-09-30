from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.services.forensic_element_identity_factory import (
    ForensicElementIdentityFactory,
)


def test_should_generate_uuid() -> None:
    result = (
        ForensicElementIdentityFactory.create(
            document_id=uuid4(),
            source_key="document:sha256",
        )
    )

    assert isinstance(result, UUID)


def test_same_identity_should_generate_same_uuid() -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory.create(
            document_id=document_id,
            source_key="image:10",
        )
    )

    second = (
        ForensicElementIdentityFactory.create(
            document_id=document_id,
            source_key="image:10",
        )
    )

    assert first == second


def test_different_documents_should_generate_different_ids() -> None:
    first = (
        ForensicElementIdentityFactory.create(
            document_id=uuid4(),
            source_key="image:10",
        )
    )

    second = (
        ForensicElementIdentityFactory.create(
            document_id=uuid4(),
            source_key="image:10",
        )
    )

    assert first != second


def test_different_source_keys_should_generate_different_ids() -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory.create(
            document_id=document_id,
            source_key="image:10",
        )
    )

    second = (
        ForensicElementIdentityFactory.create(
            document_id=document_id,
            source_key="image:11",
        )
    )

    assert first != second


def test_source_key_should_be_normalized() -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory.create(
            document_id=document_id,
            source_key=" IMAGE:10 ",
        )
    )

    second = (
        ForensicElementIdentityFactory.create(
            document_id=document_id,
            source_key="image:10",
        )
    )

    assert first == second


def test_document_sha256_should_be_deterministic() -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory
        .document_sha256(
            document_id=document_id,
        )
    )

    second = (
        ForensicElementIdentityFactory
        .document_sha256(
            document_id=document_id,
        )
    )

    assert first == second


def test_image_identity_should_use_image_index() -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory.image(
            document_id=document_id,
            image_index=0,
        )
    )

    second = (
        ForensicElementIdentityFactory.image(
            document_id=document_id,
            image_index=1,
        )
    )

    assert first != second


def test_image_hashes_should_have_distinct_identities() -> None:
    document_id = uuid4()

    sha256 = (
        ForensicElementIdentityFactory
        .image_hash(
            document_id=document_id,
            image_index=4,
            hash_type="sha256",
        )
    )

    phash = (
        ForensicElementIdentityFactory
        .image_hash(
            document_id=document_id,
            image_index=4,
            hash_type="phash",
        )
    )

    ahash = (
        ForensicElementIdentityFactory
        .image_hash(
            document_id=document_id,
            image_index=4,
            hash_type="ahash",
        )
    )

    assert sha256 != phash
    assert sha256 != ahash
    assert phash != ahash


def test_hash_type_should_be_normalized() -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory
        .image_hash(
            document_id=document_id,
            image_index=2,
            hash_type=" PHASH ",
        )
    )

    second = (
        ForensicElementIdentityFactory
        .image_hash(
            document_id=document_id,
            image_index=2,
            hash_type="phash",
        )
    )

    assert first == second


def test_barcode_identity_should_be_deterministic() -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory.barcode(
            document_id=document_id,
            barcode_index=7,
        )
    )

    second = (
        ForensicElementIdentityFactory.barcode(
            document_id=document_id,
            barcode_index=7,
        )
    )

    assert first == second


def test_qrcode_identity_should_be_deterministic() -> None:
    document_id = uuid4()

    first = (
        ForensicElementIdentityFactory.qrcode(
            document_id=document_id,
            qrcode_index=3,
        )
    )

    second = (
        ForensicElementIdentityFactory.qrcode(
            document_id=document_id,
            qrcode_index=3,
        )
    )

    assert first == second


@pytest.mark.parametrize(
    "invalid_index",
    [
        -1,
        -10,
    ],
)
def test_should_reject_negative_image_index(
    invalid_index: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="maior ou igual a zero",
    ):
        ForensicElementIdentityFactory.image(
            document_id=uuid4(),
            image_index=invalid_index,
        )


@pytest.mark.parametrize(
    "invalid_index",
    [
        -1,
        -10,
    ],
)
def test_should_reject_negative_barcode_index(
    invalid_index: int,
) -> None:
    with pytest.raises(ValueError):
        ForensicElementIdentityFactory.barcode(
            document_id=uuid4(),
            barcode_index=invalid_index,
        )


def test_should_reject_boolean_as_index() -> None:
    with pytest.raises(
        TypeError,
        match="inteiro",
    ):
        ForensicElementIdentityFactory.image(
            document_id=uuid4(),
            image_index=True,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "source_key",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_should_reject_empty_source_key(
    source_key: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="não pode ser vazio",
    ):
        ForensicElementIdentityFactory.create(
            document_id=uuid4(),
            source_key=source_key,
        )


def test_should_reject_invalid_document_id() -> None:
    with pytest.raises(
        TypeError,
        match="UUID",
    ):
        ForensicElementIdentityFactory.create(
            document_id="invalid",  # type: ignore[arg-type]
            source_key="image:1",
        )