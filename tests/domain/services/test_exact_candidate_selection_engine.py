from uuid import uuid4

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
from app.domain.services.exact_candidate_selection_engine import (
    ExactCandidateSelectionEngine,
)
from app.domain.services.forensic_canonicalizers import (
    canonicalize_digits,
)
from app.domain.services.forensic_index_registry import (
    ForensicIndexRegistry,
)
from app.domain.services.sha256_forensic_index import (
    Sha256ForensicIndex,
)


SHA = "a" * 64

NUMERIC_LINE = (
    "00190500954014481606906809350314337370000000100"
)


def create_hash_element(
    *,
    document_id=None,
    value: str = SHA,
) -> ForensicElement:
    document_id = (
        document_id or uuid4()
    )

    return ForensicElement(
        element_type=(
            ForensicElementType.HASH
        ),
        subtype="sha256",
        value=value,
        provenance=(
            ForensicProvenance(
                document_id=document_id,
                layer=(
                    ForensicDataLayer.DERIVED
                ),
                producer="test",
                producer_version="1.0",
            )
        ),
    )


def create_numeric_line_element(
    *,
    document_id=None,
    value: str = NUMERIC_LINE,
) -> ForensicElement:
    document_id = (
        document_id or uuid4()
    )

    return ForensicElement(
        element_type=(
            ForensicElementType.NUMERIC_LINE
        ),
        subtype=(
            "normalized_numeric_line"
        ),
        value=value,
        provenance=(
            ForensicProvenance(
                document_id=document_id,
                layer=(
                    ForensicDataLayer.DERIVED
                ),
                producer="test",
                producer_version="1.0",
            )
        ),
    )


def create_registry_with_sha_index(
) -> tuple[
    ForensicIndexRegistry,
    Sha256ForensicIndex,
]:
    registry = (
        ForensicIndexRegistry()
    )

    index = (
        Sha256ForensicIndex()
    )

    registry.register(
        name="sha256",
        element_type=(
            ForensicElementType.HASH
        ),
        subtype="sha256",
        index=index,
    )

    return registry, index


def test_empty_selection_should_return_empty_result(
) -> None:
    registry = (
        ForensicIndexRegistry()
    )

    result = (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[],
        )
    )

    assert result.groups == ()

    assert (
        result.stats.candidate_groups
        == 0
    )

    assert (
        result.stats
        .represented_cross_document_relations
        == 0
    )


def test_should_select_sha_group_across_documents(
) -> None:
    registry, index = (
        create_registry_with_sha_index()
    )

    first = create_hash_element()
    second = create_hash_element()

    registry.index_element(
        first
    )

    registry.index_element(
        second
    )

    result = (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[
                "sha256"
            ],
        )
    )

    assert len(
        result.groups
    ) == 1

    group = result.groups[0]

    assert (
        group.source_index
        == "sha256"
    )

    assert (
        group.element_count
        == 2
    )

    assert (
        group.document_count
        == 2
    )

    assert (
        group
        .represented_cross_document_relations
        == 1
    )


def test_same_document_group_should_be_ignored_by_default(
) -> None:
    registry, index = (
        create_registry_with_sha_index()
    )

    document_id = uuid4()

    registry.index_element(
        create_hash_element(
            document_id=(
                document_id
            )
        )
    )

    registry.index_element(
        create_hash_element(
            document_id=(
                document_id
            )
        )
    )

    result = (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[
                "sha256"
            ],
        )
    )

    assert result.groups == ()


def test_should_select_numeric_line_group(
) -> None:
    registry = (
        ForensicIndexRegistry()
    )

    index = (
        CanonicalForensicIndex(
            key_type=(
                "numeric_line"
            ),
            element_type=(
                ForensicElementType
                .NUMERIC_LINE
            ),
            subtype=(
                "normalized_numeric_line"
            ),
            canonicalizer=(
                canonicalize_digits
            ),
        )
    )

    registry.register(
        name="numeric_line",
        element_type=(
            ForensicElementType
            .NUMERIC_LINE
        ),
        subtype=(
            "normalized_numeric_line"
        ),
        index=index,
    )

    registry.index_element(
        create_numeric_line_element(
            value=(
                "00190.50095"
                "40144.816069"
                "06809.350314"
                "3"
                "37370000000100"
            )
        )
    )

    registry.index_element(
        create_numeric_line_element(
            value=NUMERIC_LINE
        )
    )

    result = (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[
                "numeric_line"
            ],
        )
    )

    assert len(
        result.groups
    ) == 1

    assert (
        result.groups[0].key_value
        == NUMERIC_LINE
    )


def test_should_use_multiple_indexes(
) -> None:
    registry = (
        ForensicIndexRegistry()
    )

    sha_index = (
        Sha256ForensicIndex()
    )

    line_index = (
        CanonicalForensicIndex(
            key_type="numeric_line",
            element_type=(
                ForensicElementType
                .NUMERIC_LINE
            ),
            subtype=(
                "normalized_numeric_line"
            ),
            canonicalizer=(
                canonicalize_digits
            ),
        )
    )

    registry.register(
        name="sha256",
        element_type=(
            ForensicElementType.HASH
        ),
        subtype="sha256",
        index=sha_index,
    )

    registry.register(
        name="numeric_line",
        element_type=(
            ForensicElementType
            .NUMERIC_LINE
        ),
        subtype=(
            "normalized_numeric_line"
        ),
        index=line_index,
    )

    for _ in range(2):
        registry.index_element(
            create_hash_element()
        )

        registry.index_element(
            create_numeric_line_element()
        )

    result = (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[
                "sha256",
                "numeric_line",
            ],
        )
    )

    assert len(
        result.groups
    ) == 2

    assert (
        result.stats.sources_used
        == 2
    )


def test_duplicate_requested_index_names_should_be_ignored(
) -> None:
    registry, index = (
        create_registry_with_sha_index()
    )

    registry.index_element(
        create_hash_element()
    )

    registry.index_element(
        create_hash_element()
    )

    result = (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[
                "sha256",
                " SHA256 ",
                "Sha256",
            ],
        )
    )

    assert len(
        result.groups
    ) == 1

    assert (
        result.stats.sources_used
        == 1
    )


def test_unknown_index_should_raise() -> None:
    registry = (
        ForensicIndexRegistry()
    )

    with pytest.raises(
        ValueError,
        match="não registrado",
    ):
        (
            ExactCandidateSelectionEngine()
            .select(
                registry=registry,
                index_names=[
                    "unknown"
                ],
            )
        )


def test_index_without_duplicate_groups_should_raise(
) -> None:
    class AddOnlyIndex:
        def add(
            self,
            element,
        ) -> bool:
            return True

    registry = (
        ForensicIndexRegistry()
    )

    registry.register(
        name="add_only",
        element_type=(
            ForensicElementType.HASH
        ),
        subtype="sha256",
        index=AddOnlyIndex(),
    )

    with pytest.raises(
        TypeError,
        match="grupos exatos",
    ):
        (
            ExactCandidateSelectionEngine()
            .select(
                registry=registry,
                index_names=[
                    "add_only"
                ],
            )
        )


def test_stats_should_count_unique_elements_and_documents(
) -> None:
    registry, index = (
        create_registry_with_sha_index()
    )

    documents = [
        uuid4(),
        uuid4(),
        uuid4(),
    ]

    for document_id in documents:
        registry.index_element(
            create_hash_element(
                document_id=(
                    document_id
                )
            )
        )

    result = (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[
                "sha256"
            ],
        )
    )

    assert (
        result.stats.unique_elements
        == 3
    )

    assert (
        result.stats.unique_documents
        == 3
    )

    assert (
        result.stats
        .represented_cross_document_relations
        == 3
    )


def test_large_exact_group_should_not_require_pair_materialization(
) -> None:
    registry, index = (
        create_registry_with_sha_index()
    )

    for _ in range(100):
        registry.index_element(
            create_hash_element()
        )

    result = (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[
                "sha256"
            ],
        )
    )

    assert len(
        result.groups
    ) == 1

    group = result.groups[0]

    assert (
        group.element_count
        == 100
    )

    assert (
        group
        .represented_cross_document_relations
        == 4950
    )

    assert not hasattr(
        group,
        "pairs",
    )