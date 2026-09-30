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
from app.domain.services.canonical_forensic_index import (
    CanonicalForensicIndex,
)
from app.domain.services.forensic_canonicalizers import (
    canonicalize_casefolded_text,
    canonicalize_compact_alphanumeric,
    canonicalize_digits,
    canonicalize_trimmed,
)


def create_element(
    *,
    document_id: UUID | None = None,
    element_id: UUID | None = None,
    element_type: ForensicElementType = (
        ForensicElementType.TEXT
    ),
    subtype: str = "name",
    value: str = "Banco Pan",
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
            layer=ForensicDataLayer.EXTRACTED,
            producer="TestExtractor",
            producer_version="1.0",
        ),
    )


def create_name_index(
) -> CanonicalForensicIndex:
    return CanonicalForensicIndex(
        key_type="canonical_name",
        element_type=ForensicElementType.TEXT,
        subtype="name",
        canonicalizer=canonicalize_casefolded_text,
    )


def test_should_start_empty() -> None:
    index = create_name_index()

    assert len(index) == 0
    assert index.duplicate_groups() == ()


def test_should_add_and_lookup_element() -> None:
    index = create_name_index()

    element = create_element(
        value="Banco Pan",
    )

    assert index.add(element) is True

    assert index.lookup(
        "Banco Pan"
    ) == (
        element,
    )


def test_should_group_case_variations() -> None:
    index = create_name_index()

    first = create_element(
        value="BANCO PAN",
    )

    second = create_element(
        value="banco pan",
    )

    index.add_many(
        [first, second]
    )

    groups = index.duplicate_groups()

    assert len(groups) == 1

    assert (
        groups[0].key_value
        == "banco pan"
    )


def test_should_group_outer_whitespace_variations() -> None:
    index = create_name_index()

    first = create_element(
        value="  Banco Pan  ",
    )

    second = create_element(
        value="Banco Pan",
    )

    index.add_many(
        [first, second]
    )

    assert len(
        index.duplicate_groups()
    ) == 1


def test_should_preserve_original_values() -> None:
    index = create_name_index()

    original = "  BANCO PAN  "

    element = create_element(
        value=original,
    )

    index.add(element)

    assert element.value == original

    assert (
        index.canonical_value_of(
            element.element_id
        )
        == "banco pan"
    )


def test_unique_values_should_not_create_groups() -> None:
    index = create_name_index()

    index.add_many(
        [
            create_element(
                value="Banco A",
            ),
            create_element(
                value="Banco B",
            ),
        ]
    )

    assert (
        index.duplicate_groups()
        == ()
    )


def test_should_create_cross_document_group() -> None:
    index = create_name_index()

    first_document = uuid4()
    second_document = uuid4()

    index.add_many(
        [
            create_element(
                document_id=first_document,
                value="Banco Pan",
            ),
            create_element(
                document_id=second_document,
                value="BANCO PAN",
            ),
        ]
    )

    groups = index.duplicate_groups(
        cross_document_only=True,
    )

    assert len(groups) == 1
    assert groups[0].document_count == 2


def test_cross_document_filter_should_ignore_same_document_group(
) -> None:
    index = create_name_index()

    document_id = uuid4()

    index.add_many(
        [
            create_element(
                document_id=document_id,
                value="Banco Pan",
            ),
            create_element(
                document_id=document_id,
                value="BANCO PAN",
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


def test_should_represent_many_relations_without_pairs() -> None:
    index = create_name_index()

    elements = [
        create_element(
            document_id=uuid4(),
            value="Banco Pan",
        )
        for _ in range(100)
    ]

    index.add_many(elements)

    group = (
        index.duplicate_groups(
            cross_document_only=True,
        )[0]
    )

    assert group.element_count == 100

    assert (
        group.cross_document_pairwise_relations
        == 4950
    )


def test_should_reject_wrong_element_type() -> None:
    index = create_name_index()

    element = create_element(
        element_type=ForensicElementType.IMAGE,
    )

    with pytest.raises(
        ValueError,
        match="element_type",
    ):
        index.add(element)


def test_should_reject_wrong_subtype() -> None:
    index = create_name_index()

    element = create_element(
        subtype="address",
    )

    with pytest.raises(
        ValueError,
        match="subtype",
    ):
        index.add(element)


def test_should_be_idempotent() -> None:
    index = create_name_index()

    element = create_element()

    assert index.add(element) is True
    assert index.add(element) is False

    assert len(index) == 1


def test_should_reject_same_id_with_different_content() -> None:
    index = create_name_index()

    element_id = uuid4()
    document_id = uuid4()

    first = create_element(
        element_id=element_id,
        document_id=document_id,
        value="Banco A",
    )

    second = create_element(
        element_id=element_id,
        document_id=document_id,
        value="Banco B",
    )

    index.add(first)

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        index.add(second)


def test_should_add_many() -> None:
    index = create_name_index()

    added = index.add_many(
        [
            create_element(
                value="Banco A",
            ),
            create_element(
                value="Banco B",
            ),
        ]
    )

    assert added == 2
    assert len(index) == 2


def test_should_build_stats() -> None:
    index = create_name_index()

    index.add_many(
        [
            create_element(
                document_id=uuid4(),
                value="Banco Pan",
            ),
            create_element(
                document_id=uuid4(),
                value="BANCO PAN",
            ),
            create_element(
                document_id=uuid4(),
                value="Outro Banco",
            ),
        ]
    )

    stats = index.stats()

    assert stats.key_type == "canonical_name"
    assert stats.element_type is ForensicElementType.TEXT
    assert stats.subtype == "name"

    assert stats.indexed_elements == 3
    assert stats.unique_keys == 2

    assert stats.duplicate_groups == 1
    assert stats.cross_document_groups == 1

    assert (
        stats.elements_in_duplicate_groups
        == 2
    )

    assert (
        stats.represented_pairwise_relations
        == 1
    )


def test_digits_canonicalizer_should_ignore_formatting() -> None:
    first = canonicalize_digits(
        "123.456.789-00"
    )

    second = canonicalize_digits(
        "12345678900"
    )

    assert first == "12345678900"
    assert second == "12345678900"


def test_digits_index_should_group_formatted_values() -> None:
    index = CanonicalForensicIndex(
        key_type="cpf",
        element_type=ForensicElementType.TEXT,
        subtype="cpf",
        canonicalizer=canonicalize_digits,
    )

    first = create_element(
        subtype="cpf",
        value="123.456.789-00",
    )

    second = create_element(
        subtype="cpf",
        value="12345678900",
    )

    index.add_many(
        [first, second]
    )

    groups = index.duplicate_groups()

    assert len(groups) == 1
    assert groups[0].key_value == "12345678900"


def test_compact_alphanumeric_should_remove_formatting() -> None:
    assert (
        canonicalize_compact_alphanumeric(
            "Banco-PAN S/A"
        )
        == "bancopansa"
    )


def test_trimmed_canonicalizer_should_preserve_internal_content(
) -> None:
    assert (
        canonicalize_trimmed(
            "  Banco   PAN  "
        )
        == "Banco   PAN"
    )


def test_should_reject_canonicalizer_returning_empty_value() -> None:
    def empty_canonicalizer(
        value: str,
    ) -> str:
        return ""

    index = CanonicalForensicIndex(
        key_type="test",
        element_type=ForensicElementType.TEXT,
        subtype="name",
        canonicalizer=empty_canonicalizer,
    )

    with pytest.raises(
        ValueError,
        match="non-empty",
    ):
        index.add(
            create_element()
        )


def test_should_reject_canonicalizer_returning_non_string() -> None:
    def invalid_canonicalizer(
        value: str,
    ) -> str:
        return 123  # type: ignore[return-value]

    index = CanonicalForensicIndex(
        key_type="test",
        element_type=ForensicElementType.TEXT,
        subtype="name",
        canonicalizer=invalid_canonicalizer,
    )

    with pytest.raises(
        TypeError,
        match="return a string",
    ):
        index.add(
            create_element()
        )