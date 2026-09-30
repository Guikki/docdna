from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.domain.models.forensic_data_layer import (
    ForensicDataLayer,
)
from app.domain.models.forensic_element import (
    ForensicElement,
)
from app.domain.models.forensic_element_type import (
    ForensicElementType,
)
from app.domain.models.forensic_provenance import (
    ForensicProvenance,
)
from app.domain.services.sha256_forensic_index import (
    Sha256ForensicIndex,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def create_hash_element(
    *,
    document_id: UUID | None = None,
    element_id: UUID | None = None,
    value: str = HASH_A,
    subtype: str = "sha256",
    element_type: ForensicElementType = (
        ForensicElementType.HASH
    ),
) -> ForensicElement:
    return ForensicElement(
        element_id=element_id or uuid4(),
        element_type=element_type,
        subtype=subtype,
        value=value,
        provenance=ForensicProvenance(
            document_id=(
                document_id or uuid4()
            ),
            layer=ForensicDataLayer.DERIVED,
            producer="ImageHashAnalyzer",
            producer_version="1.0",
        ),
    )


def test_should_start_empty() -> None:
    index = Sha256ForensicIndex()

    assert len(index) == 0
    assert index.duplicate_groups() == ()


def test_should_add_sha256_element() -> None:
    index = Sha256ForensicIndex()
    element = create_hash_element()

    assert index.add(element) is True
    assert len(index) == 1

    assert index.lookup(HASH_A) == (
        element,
    )


def test_should_normalize_hash_for_index_key() -> None:
    index = Sha256ForensicIndex()

    original_value = (
        "  " + HASH_A.upper() + "  "
    )

    element = create_hash_element(
        value=original_value,
    )

    index.add(element)

    assert index.lookup(HASH_A) == (
        element,
    )

    assert index.lookup(
        HASH_A.upper()
    ) == (
        element,
    )


def test_should_preserve_original_hash_value() -> None:
    index = Sha256ForensicIndex()

    original_value = (
        "  " + HASH_A.upper() + "  "
    )

    element = create_hash_element(
        value=original_value,
    )

    index.add(element)

    assert element.value == original_value


def test_should_be_idempotent_for_same_element() -> None:
    index = Sha256ForensicIndex()
    element = create_hash_element()

    assert index.add(element) is True
    assert index.add(element) is False
    assert len(index) == 1


def test_should_reject_same_id_with_different_data() -> None:
    index = Sha256ForensicIndex()

    element_id = uuid4()
    document_id = uuid4()

    first = create_hash_element(
        element_id=element_id,
        document_id=document_id,
        value=HASH_A,
    )

    second = create_hash_element(
        element_id=element_id,
        document_id=document_id,
        value=HASH_B,
    )

    index.add(first)

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        index.add(second)


def test_should_reject_non_hash_element() -> None:
    index = Sha256ForensicIndex()

    element = create_hash_element(
        element_type=ForensicElementType.TEXT,
    )

    with pytest.raises(
        ValueError,
        match="HASH elements",
    ):
        index.add(element)


def test_should_reject_wrong_hash_subtype() -> None:
    index = Sha256ForensicIndex()

    element = create_hash_element(
        subtype="phash",
    )

    with pytest.raises(
        ValueError,
        match="sha256 elements",
    ):
        index.add(element)


def test_should_reject_invalid_hash_length() -> None:
    index = Sha256ForensicIndex()

    element = create_hash_element(
        value="a" * 63,
    )

    with pytest.raises(
        ValueError,
        match="64 hexadecimal",
    ):
        index.add(element)


def test_should_reject_non_hexadecimal_hash() -> None:
    index = Sha256ForensicIndex()

    element = create_hash_element(
        value="g" * 64,
    )

    with pytest.raises(
        ValueError,
        match="hexadecimal",
    ):
        index.add(element)


def test_should_return_empty_lookup_for_unknown_hash() -> None:
    index = Sha256ForensicIndex()

    assert index.lookup(HASH_C) == ()


def test_should_create_duplicate_group() -> None:
    index = Sha256ForensicIndex()

    first = create_hash_element(
        value=HASH_A,
    )

    second = create_hash_element(
        value=HASH_A,
    )

    index.add_many(
        [first, second]
    )

    groups = index.duplicate_groups()

    assert len(groups) == 1

    group = groups[0]

    assert group.key_type == "sha256"
    assert group.key_value == HASH_A

    assert group.element_ids == (
        first.element_id,
        second.element_id,
    )

    assert group.element_count == 2
    assert group.pairwise_relations == 1


def test_should_not_group_unique_hashes() -> None:
    index = Sha256ForensicIndex()

    index.add_many(
        [
            create_hash_element(
                value=HASH_A,
            ),
            create_hash_element(
                value=HASH_B,
            ),
        ]
    )

    assert index.duplicate_groups() == ()


def test_should_separate_different_duplicate_hashes() -> None:
    index = Sha256ForensicIndex()

    index.add_many(
        [
            create_hash_element(
                value=HASH_A,
            ),
            create_hash_element(
                value=HASH_A,
            ),
            create_hash_element(
                value=HASH_B,
            ),
            create_hash_element(
                value=HASH_B,
            ),
        ]
    )

    groups = index.duplicate_groups()

    assert len(groups) == 2

    assert {
        group.key_value
        for group in groups
    } == {
        HASH_A,
        HASH_B,
    }


def test_cross_document_filter_should_ignore_same_document_group(
) -> None:
    index = Sha256ForensicIndex()
    document_id = uuid4()

    index.add_many(
        [
            create_hash_element(
                document_id=document_id,
                value=HASH_A,
            ),
            create_hash_element(
                document_id=document_id,
                value=HASH_A,
            ),
        ]
    )

    assert len(
        index.duplicate_groups()
    ) == 1

    assert (
        index.duplicate_groups(
            cross_document_only=True,
        )
        == ()
    )


def test_should_create_cross_document_group() -> None:
    index = Sha256ForensicIndex()

    first_document = uuid4()
    second_document = uuid4()

    index.add_many(
        [
            create_hash_element(
                document_id=first_document,
                value=HASH_A,
            ),
            create_hash_element(
                document_id=second_document,
                value=HASH_A,
            ),
        ]
    )

    groups = index.duplicate_groups(
        cross_document_only=True,
    )

    assert len(groups) == 1

    assert groups[0].is_cross_document is True
    assert groups[0].document_count == 2


def test_group_should_calculate_pairwise_relations_without_creating_pairs(
) -> None:
    index = Sha256ForensicIndex()

    documents = [
        uuid4()
        for _ in range(100)
    ]

    index.add_many(
        [
            create_hash_element(
                document_id=document_id,
                value=HASH_A,
            )
            for document_id in documents
        ]
    )

    groups = index.duplicate_groups(
        cross_document_only=True,
    )

    assert len(groups) == 1

    group = groups[0]

    assert group.element_count == 100

    assert (
        group.pairwise_relations
        == 4950
    )

    assert (
        group.cross_document_pairwise_relations
        == 4950
    )


def test_cross_document_relations_should_ignore_pairs_inside_same_document(
) -> None:
    index = Sha256ForensicIndex()

    first_document = uuid4()
    second_document = uuid4()

    index.add_many(
        [
            create_hash_element(
                document_id=first_document,
                value=HASH_A,
            ),
            create_hash_element(
                document_id=first_document,
                value=HASH_A,
            ),
            create_hash_element(
                document_id=second_document,
                value=HASH_A,
            ),
        ]
    )

    group = index.duplicate_groups()[0]

    assert group.pairwise_relations == 3

    assert (
        group.cross_document_pairwise_relations
        == 2
    )


def test_should_add_many_elements() -> None:
    index = Sha256ForensicIndex()

    first = create_hash_element(
        value=HASH_A,
    )

    second = create_hash_element(
        value=HASH_B,
    )

    added = index.add_many(
        [first, second]
    )

    assert added == 2
    assert len(index) == 2


def test_should_build_stats() -> None:
    index = Sha256ForensicIndex()

    first_document = uuid4()
    second_document = uuid4()
    third_document = uuid4()

    index.add_many(
        [
            create_hash_element(
                document_id=first_document,
                value=HASH_A,
            ),
            create_hash_element(
                document_id=second_document,
                value=HASH_A,
            ),
            create_hash_element(
                document_id=third_document,
                value=HASH_A,
            ),
            create_hash_element(
                document_id=first_document,
                value=HASH_B,
            ),
        ]
    )

    stats = index.stats()

    assert stats.indexed_elements == 4
    assert stats.unique_hashes == 2

    assert stats.duplicate_hash_groups == 1
    assert stats.cross_document_groups == 1

    assert (
        stats.elements_in_duplicate_groups
        == 3
    )

    assert (
        stats.elements_in_cross_document_groups
        == 3
    )

    assert (
        stats.represented_pairwise_relations
        == 3
    )

    assert (
        stats.represented_cross_document_pairwise_relations
        == 3
    )