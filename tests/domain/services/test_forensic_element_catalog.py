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
from app.domain.services.forensic_element_catalog import (
    ForensicElementCatalog,
)


def create_element(
    *,
    document_id: UUID | None = None,
    element_id: UUID | None = None,
    element_type: ForensicElementType = (
        ForensicElementType.TEXT
    ),
    subtype: str | None = "ocr_text",
    value: str | None = "conteúdo",
    layer: ForensicDataLayer = (
        ForensicDataLayer.EXTRACTED
    ),
    parent_element_id: UUID | None = None,
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
            layer=layer,
            producer="TestProducer",
            producer_version="1.0",
            parent_element_id=(
                parent_element_id
            ),
        ),
    )


def test_should_start_empty() -> None:
    catalog = ForensicElementCatalog()

    assert len(catalog) == 0
    assert catalog.all() == ()


def test_should_add_element() -> None:
    catalog = ForensicElementCatalog()
    element = create_element()

    added = catalog.add(element)

    assert added is True
    assert len(catalog) == 1
    assert catalog.get(element.element_id) is element


def test_should_preserve_insertion_order() -> None:
    catalog = ForensicElementCatalog()

    first = create_element()
    second = create_element()
    third = create_element()

    catalog.add(first)
    catalog.add(second)
    catalog.add(third)

    assert catalog.all() == (
        first,
        second,
        third,
    )


def test_should_be_idempotent_for_same_element() -> None:
    catalog = ForensicElementCatalog()
    element = create_element()

    assert catalog.add(element) is True
    assert catalog.add(element) is False

    assert len(catalog) == 1


def test_should_reject_same_id_with_different_data() -> None:
    catalog = ForensicElementCatalog()
    element_id = uuid4()
    document_id = uuid4()

    first = create_element(
        element_id=element_id,
        document_id=document_id,
        value="primeiro",
    )

    second = create_element(
        element_id=element_id,
        document_id=document_id,
        value="segundo",
    )

    catalog.add(first)

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        catalog.add(second)


def test_should_find_elements_by_document() -> None:
    catalog = ForensicElementCatalog()

    first_document = uuid4()
    second_document = uuid4()

    first = create_element(
        document_id=first_document,
    )

    second = create_element(
        document_id=first_document,
        element_type=ForensicElementType.IMAGE,
        subtype="generic_image",
    )

    third = create_element(
        document_id=second_document,
    )

    catalog.add_many(
        [first, second, third]
    )

    assert catalog.by_document(
        first_document
    ) == (
        first,
        second,
    )

    assert catalog.by_document(
        second_document
    ) == (
        third,
    )


def test_should_find_elements_by_type() -> None:
    catalog = ForensicElementCatalog()

    first = create_element(
        element_type=ForensicElementType.IMAGE,
        subtype="generic_image",
    )

    second = create_element(
        element_type=ForensicElementType.IMAGE,
        subtype="logo",
    )

    third = create_element(
        element_type=ForensicElementType.TEXT,
        subtype="ocr_text",
    )

    catalog.add_many(
        [first, second, third]
    )

    assert catalog.by_type(
        ForensicElementType.IMAGE
    ) == (
        first,
        second,
    )


def test_should_find_elements_by_subtype() -> None:
    catalog = ForensicElementCatalog()

    first = create_element(
        subtype="sha256",
        element_type=ForensicElementType.HASH,
    )

    second = create_element(
        subtype="sha256",
        element_type=ForensicElementType.HASH,
    )

    third = create_element(
        subtype="phash",
        element_type=ForensicElementType.HASH,
    )

    catalog.add_many(
        [first, second, third]
    )

    assert catalog.by_subtype(
        "sha256"
    ) == (
        first,
        second,
    )


def test_should_find_elements_by_layer() -> None:
    catalog = ForensicElementCatalog()

    extracted = create_element(
        layer=ForensicDataLayer.EXTRACTED,
    )

    derived = create_element(
        layer=ForensicDataLayer.DERIVED,
    )

    catalog.add_many(
        [extracted, derived]
    )

    assert catalog.by_layer(
        ForensicDataLayer.DERIVED
    ) == (
        derived,
    )


def test_should_find_children_from_parent() -> None:
    catalog = ForensicElementCatalog()
    document_id = uuid4()

    parent = create_element(
        document_id=document_id,
        element_type=ForensicElementType.IMAGE,
        subtype="generic_image",
    )

    sha = create_element(
        document_id=document_id,
        element_type=ForensicElementType.HASH,
        subtype="sha256",
        layer=ForensicDataLayer.DERIVED,
        parent_element_id=parent.element_id,
    )

    phash = create_element(
        document_id=document_id,
        element_type=ForensicElementType.HASH,
        subtype="phash",
        layer=ForensicDataLayer.DERIVED,
        parent_element_id=parent.element_id,
    )

    catalog.add_many(
        [parent, sha, phash]
    )

    assert catalog.children_of(
        parent.element_id
    ) == (
        sha,
        phash,
    )


def test_should_allow_child_before_parent() -> None:
    catalog = ForensicElementCatalog()
    document_id = uuid4()
    parent_id = uuid4()

    child = create_element(
        document_id=document_id,
        element_type=ForensicElementType.HASH,
        subtype="sha256",
        layer=ForensicDataLayer.DERIVED,
        parent_element_id=parent_id,
    )

    parent = create_element(
        document_id=document_id,
        element_id=parent_id,
        element_type=ForensicElementType.IMAGE,
        subtype="generic_image",
    )

    catalog.add(child)
    catalog.add(parent)

    assert catalog.children_of(
        parent_id
    ) == (
        child,
    )


def test_should_reject_cross_document_parent() -> None:
    catalog = ForensicElementCatalog()

    parent = create_element(
        document_id=uuid4(),
        element_type=ForensicElementType.IMAGE,
        subtype="generic_image",
    )

    child = create_element(
        document_id=uuid4(),
        element_type=ForensicElementType.HASH,
        subtype="sha256",
        layer=ForensicDataLayer.DERIVED,
        parent_element_id=parent.element_id,
    )

    catalog.add(parent)

    with pytest.raises(
        ValueError,
        match="same document",
    ):
        catalog.add(child)


def test_should_detect_cross_document_child_when_parent_arrives_later(
) -> None:
    catalog = ForensicElementCatalog()

    parent_id = uuid4()

    child = create_element(
        document_id=uuid4(),
        element_type=ForensicElementType.HASH,
        subtype="sha256",
        layer=ForensicDataLayer.DERIVED,
        parent_element_id=parent_id,
    )

    parent = create_element(
        document_id=uuid4(),
        element_id=parent_id,
        element_type=ForensicElementType.IMAGE,
        subtype="generic_image",
    )

    catalog.add(child)

    with pytest.raises(
        ValueError,
        match="same document",
    ):
        catalog.add(parent)


def test_should_add_many_elements() -> None:
    catalog = ForensicElementCatalog()

    elements = [
        create_element(),
        create_element(),
        create_element(),
    ]

    added = catalog.add_many(elements)

    assert added == 3
    assert len(catalog) == 3


def test_add_many_should_not_count_existing_element() -> None:
    catalog = ForensicElementCatalog()

    first = create_element()
    second = create_element()

    catalog.add(first)

    added = catalog.add_many(
        [first, second]
    )

    assert added == 1
    assert len(catalog) == 2


def test_should_build_catalog_stats() -> None:
    catalog = ForensicElementCatalog()

    first_document = uuid4()
    second_document = uuid4()

    catalog.add_many(
        [
            create_element(
                document_id=first_document,
                element_type=ForensicElementType.TEXT,
                subtype="ocr_text",
                layer=ForensicDataLayer.EXTRACTED,
            ),
            create_element(
                document_id=first_document,
                element_type=ForensicElementType.HASH,
                subtype="sha256",
                layer=ForensicDataLayer.DERIVED,
            ),
            create_element(
                document_id=second_document,
                element_type=ForensicElementType.HASH,
                subtype="sha256",
                layer=ForensicDataLayer.DERIVED,
            ),
        ]
    )

    stats = catalog.stats()

    assert stats.total_elements == 3
    assert stats.document_count == 2

    assert (
        stats.by_type[
            ForensicElementType.TEXT
        ]
        == 1
    )

    assert (
        stats.by_type[
            ForensicElementType.HASH
        ]
        == 2
    )

    assert stats.by_subtype["sha256"] == 2

    assert (
        stats.by_layer[
            ForensicDataLayer.DERIVED
        ]
        == 2
    )


def test_stats_mappings_should_be_read_only() -> None:
    catalog = ForensicElementCatalog()

    catalog.add(
        create_element(
            element_type=ForensicElementType.HASH,
            subtype="sha256",
        )
    )

    stats = catalog.stats()

    with pytest.raises(TypeError):
        stats.by_subtype["sha256"] = 999  # type: ignore[index]


def test_should_return_empty_results_for_unknown_indexes() -> None:
    catalog = ForensicElementCatalog()

    assert catalog.by_document(uuid4()) == ()

    assert catalog.by_type(
        ForensicElementType.QRCODE
    ) == ()

    assert catalog.by_subtype(
        "unknown"
    ) == ()

    assert catalog.by_layer(
        ForensicDataLayer.ANALYTICAL
    ) == ()

    assert catalog.children_of(
        uuid4()
    ) == ()


def test_should_reject_invalid_element() -> None:
    catalog = ForensicElementCatalog()

    with pytest.raises(TypeError):
        catalog.add(
            "invalid"  # type: ignore[arg-type]
        )


def test_should_reject_invalid_subtype_query() -> None:
    catalog = ForensicElementCatalog()

    with pytest.raises(ValueError):
        catalog.by_subtype("   ")