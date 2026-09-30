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
    canonicalize_digits,
)
from app.domain.services.forensic_element_catalog import (
    ForensicElementCatalog,
)
from app.domain.services.forensic_index_registry import (
    ForensicIndexRegistry,
)
from app.domain.services.sha256_forensic_index import (
    Sha256ForensicIndex,
)


HASH_A = "a" * 64


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
            producer="TestProducer",
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


def create_cpf_index(
) -> CanonicalForensicIndex:
    return CanonicalForensicIndex(
        key_type="cpf",
        element_type=ForensicElementType.TEXT,
        subtype="cpf",
        canonicalizer=canonicalize_digits,
    )


def register_name_index(
    registry: ForensicIndexRegistry,
    *,
    name: str = "names",
) -> CanonicalForensicIndex:
    index = create_name_index()

    registry.register(
        name=name,
        element_type=ForensicElementType.TEXT,
        subtype="name",
        index=index,
    )

    return index


def test_should_start_empty() -> None:
    registry = ForensicIndexRegistry()

    assert len(registry) == 0
    assert registry.index_names() == ()

    stats = registry.stats()

    assert stats.registered_indexes == 0
    assert stats.indexed_elements == 0
    assert stats.index_memberships == 0


def test_should_register_index() -> None:
    registry = ForensicIndexRegistry()

    index = register_name_index(
        registry
    )

    assert len(registry) == 1
    assert registry.index_names() == (
        "names",
    )

    assert (
        registry.get_index("names")
        is index
    )


def test_should_lookup_index_case_insensitively() -> None:
    registry = ForensicIndexRegistry()

    index = register_name_index(
        registry,
        name="Canonical Names",
    )

    assert (
        registry.get_index(
            "canonical names"
        )
        is index
    )

    assert (
        registry.get_index(
            "  CANONICAL NAMES  "
        )
        is index
    )


def test_should_reject_duplicate_index_name_case_insensitively(
) -> None:
    registry = ForensicIndexRegistry()

    register_name_index(
        registry,
        name="Names",
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        register_name_index(
            registry,
            name="  names  ",
        )


def test_should_reject_index_without_add_method() -> None:
    registry = ForensicIndexRegistry()

    with pytest.raises(
        TypeError,
        match="add",
    ):
        registry.register(
            name="invalid",
            element_type=ForensicElementType.TEXT,
            subtype="name",
            index=object(),  # type: ignore[arg-type]
        )


def test_should_route_element_to_matching_index() -> None:
    registry = ForensicIndexRegistry()

    index = register_name_index(
        registry
    )

    element = create_element(
        subtype="name",
        value="Banco Pan",
    )

    result = registry.index_element(
        element
    )

    assert result.element_id == element.element_id

    assert result.matched_indexes == (
        "names",
    )

    assert (
        result.newly_indexed_indexes
        == ("names",)
    )

    assert result.matched_count == 1
    assert result.newly_indexed_count == 1
    assert result.was_indexed is True

    assert index.lookup(
        "Banco Pan"
    ) == (
        element,
    )


def test_should_not_route_wrong_element_type() -> None:
    registry = ForensicIndexRegistry()

    register_name_index(
        registry
    )

    element = create_element(
        element_type=ForensicElementType.IMAGE,
        subtype="name",
    )

    result = registry.index_element(
        element
    )

    assert result.matched_indexes == ()
    assert result.was_indexed is False


def test_should_not_route_wrong_subtype() -> None:
    registry = ForensicIndexRegistry()

    register_name_index(
        registry
    )

    element = create_element(
        subtype="address",
    )

    result = registry.index_element(
        element
    )

    assert result.matched_indexes == ()
    assert result.was_indexed is False


def test_should_match_subtype_case_insensitively() -> None:
    registry = ForensicIndexRegistry()

    index = create_name_index()

    registry.register(
        name="names",
        element_type=ForensicElementType.TEXT,
        subtype="  NAME  ",
        index=index,
    )

    element = create_element(
        subtype="Name",
    )

    result = registry.index_element(
        element
    )

    assert result.matched_indexes == (
        "names",
    )


def test_same_element_can_belong_to_multiple_indexes() -> None:
    registry = ForensicIndexRegistry()

    first_index = create_name_index()
    second_index = create_name_index()

    registry.register(
        name="names-primary",
        element_type=ForensicElementType.TEXT,
        subtype="name",
        index=first_index,
    )

    registry.register(
        name="names-secondary",
        element_type=ForensicElementType.TEXT,
        subtype="name",
        index=second_index,
    )

    element = create_element()

    result = registry.index_element(
        element
    )

    assert result.matched_indexes == (
        "names-primary",
        "names-secondary",
    )

    assert (
        registry.memberships(
            element.element_id
        )
        == (
            "names-primary",
            "names-secondary",
        )
    )


def test_reindexing_same_element_should_be_idempotent() -> None:
    registry = ForensicIndexRegistry()

    register_name_index(
        registry
    )

    element = create_element()

    first = registry.index_element(
        element
    )

    second = registry.index_element(
        element
    )

    assert first.newly_indexed_indexes == (
        "names",
    )

    assert second.matched_indexes == (
        "names",
    )

    assert second.newly_indexed_indexes == ()

    assert (
        registry.memberships(
            element.element_id
        )
        == ("names",)
    )


def test_should_index_many_elements() -> None:
    registry = ForensicIndexRegistry()

    register_name_index(
        registry
    )

    first = create_element(
        value="Banco A",
    )

    second = create_element(
        value="Banco B",
    )

    results = registry.index_many(
        [first, second]
    )

    assert len(results) == 2

    assert all(
        result.was_indexed
        for result in results
    )


def test_should_index_catalog() -> None:
    catalog = ForensicElementCatalog()

    first = create_element(
        value="Banco A",
    )

    second = create_element(
        value="Banco B",
    )

    catalog.add_many(
        [first, second]
    )

    registry = ForensicIndexRegistry()

    index = register_name_index(
        registry
    )

    results = registry.index_catalog(
        catalog
    )

    assert len(results) == 2
    assert len(index) == 2


def test_should_return_empty_memberships_for_unknown_element() -> None:
    registry = ForensicIndexRegistry()

    assert registry.memberships(
        uuid4()
    ) == ()


def test_should_return_none_for_unknown_index() -> None:
    registry = ForensicIndexRegistry()

    assert (
        registry.get_index(
            "unknown"
        )
        is None
    )


def test_should_build_registry_stats() -> None:
    registry = ForensicIndexRegistry()

    first_index = create_name_index()
    second_index = create_name_index()

    registry.register(
        name="names-a",
        element_type=ForensicElementType.TEXT,
        subtype="name",
        index=first_index,
    )

    registry.register(
        name="names-b",
        element_type=ForensicElementType.TEXT,
        subtype="name",
        index=second_index,
    )

    first = create_element(
        value="Banco A",
    )

    second = create_element(
        value="Banco B",
    )

    registry.index_many(
        [first, second]
    )

    stats = registry.stats()

    assert stats.registered_indexes == 2

    assert stats.indexed_elements == 2

    assert stats.index_memberships == 4

    assert stats.by_index["names-a"] == 2
    assert stats.by_index["names-b"] == 2


def test_stats_mapping_should_be_read_only() -> None:
    registry = ForensicIndexRegistry()

    register_name_index(
        registry
    )

    registry.index_element(
        create_element()
    )

    stats = registry.stats()

    with pytest.raises(TypeError):
        stats.by_index["names"] = 999  # type: ignore[index]


def test_should_support_sha256_index() -> None:
    registry = ForensicIndexRegistry()

    sha_index = Sha256ForensicIndex()

    registry.register(
        name="sha256",
        element_type=ForensicElementType.HASH,
        subtype="sha256",
        index=sha_index,
    )

    first = create_element(
        document_id=uuid4(),
        element_type=ForensicElementType.HASH,
        subtype="sha256",
        value=HASH_A,
    )

    second = create_element(
        document_id=uuid4(),
        element_type=ForensicElementType.HASH,
        subtype="sha256",
        value=HASH_A.upper(),
    )

    registry.index_many(
        [first, second]
    )

    groups = (
        sha_index.duplicate_groups(
            cross_document_only=True,
        )
    )

    assert len(groups) == 1

    assert groups[0].element_count == 2


def test_should_support_different_subtypes_simultaneously() -> None:
    registry = ForensicIndexRegistry()

    name_index = create_name_index()
    cpf_index = create_cpf_index()

    registry.register(
        name="names",
        element_type=ForensicElementType.TEXT,
        subtype="name",
        index=name_index,
    )

    registry.register(
        name="cpf",
        element_type=ForensicElementType.TEXT,
        subtype="cpf",
        index=cpf_index,
    )

    name = create_element(
        subtype="name",
        value="Banco Pan",
    )

    cpf = create_element(
        subtype="cpf",
        value="123.456.789-00",
    )

    registry.index_many(
        [name, cpf]
    )

    assert name_index.lookup(
        "BANCO PAN"
    ) == (
        name,
    )

    assert cpf_index.lookup(
        "12345678900"
    ) == (
        cpf,
    )


def test_should_reject_invalid_element() -> None:
    registry = ForensicIndexRegistry()

    with pytest.raises(TypeError):
        registry.index_element(
            "invalid"  # type: ignore[arg-type]
        )


def test_should_reject_invalid_catalog() -> None:
    registry = ForensicIndexRegistry()

    with pytest.raises(TypeError):
        registry.index_catalog(
            "invalid"  # type: ignore[arg-type]
        )