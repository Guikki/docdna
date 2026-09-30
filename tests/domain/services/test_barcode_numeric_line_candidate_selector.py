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
from app.domain.services.barcode_numeric_line_candidate_selector import (
    BarcodeNumericLineCandidateSelector,
)
from app.domain.services.canonical_forensic_index import (
    CanonicalForensicIndex,
)
from app.domain.services.exact_candidate_selection_engine import (
    ExactCandidateSelectionEngine,
)
from app.domain.services.forensic_canonicalizers import (
    canonicalize_compact_alphanumeric,
)
from app.domain.services.forensic_element_catalog import (
    ForensicElementCatalog,
)
from app.domain.services.forensic_index_registry import (
    ForensicIndexRegistry,
)


BARCODE = (
    "00193373700000001000500940144816060680935031"
)

LINE_A = (
    "00190500954014481606906809350314337370000000100"
)

LINE_B = (
    "23793381286000000000339999850106123456789012"
)


def create_barcode(
    *,
    document_id: UUID,
    value: str = BARCODE,
) -> ForensicElement:
    return ForensicElement(
        element_type=(
            ForensicElementType.BARCODE
        ),
        subtype="itf",
        value=value,
        provenance=(
            ForensicProvenance(
                document_id=document_id,
                layer=(
                    ForensicDataLayer.EXTRACTED
                ),
                producer="test",
                producer_version="1.0",
            )
        ),
    )


def create_normalized_line(
    *,
    document_id: UUID,
    value: str,
) -> ForensicElement:
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


def create_raw_line(
    *,
    document_id: UUID,
    value: str,
) -> ForensicElement:
    return ForensicElement(
        element_type=(
            ForensicElementType.NUMERIC_LINE
        ),
        subtype="printed_numeric_line",
        value=value,
        provenance=(
            ForensicProvenance(
                document_id=document_id,
                layer=(
                    ForensicDataLayer.EXTRACTED
                ),
                producer="test",
                producer_version="1.0",
            )
        ),
    )


def build_exact_candidates(
    *,
    catalog: ForensicElementCatalog,
    barcodes: list[ForensicElement],
):
    registry = (
        ForensicIndexRegistry()
    )

    index = CanonicalForensicIndex(
        key_type="itf_content",
        element_type=(
            ForensicElementType.BARCODE
        ),
        subtype="itf",
        canonicalizer=(
            canonicalize_compact_alphanumeric
        ),
    )

    registry.register(
        name="itf",
        element_type=(
            ForensicElementType.BARCODE
        ),
        subtype="itf",
        index=index,
    )

    for barcode in barcodes:
        registry.index_element(
            barcode
        )

    return (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[
                "itf"
            ],
        )
    )


def select(
    *,
    elements: list[ForensicElement],
    barcodes: list[ForensicElement],
    source_indexes=None,
):
    catalog = (
        ForensicElementCatalog()
    )

    catalog.add_many(
        elements
    )

    exact_candidates = (
        build_exact_candidates(
            catalog=catalog,
            barcodes=barcodes,
        )
    )

    return (
        BarcodeNumericLineCandidateSelector()
        .select(
            catalog=catalog,
            exact_candidates=(
                exact_candidates
            ),
            source_indexes=(
                source_indexes
                if source_indexes
                is not None
                else ["itf"]
            ),
        )
    )


def test_should_select_different_lines_for_same_barcode(
) -> None:
    first_document = uuid4()
    second_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
    ]

    elements = [
        *barcodes,
        create_normalized_line(
            document_id=first_document,
            value=LINE_A,
        ),
        create_normalized_line(
            document_id=second_document,
            value=LINE_B,
        ),
    ]

    result = select(
        elements=elements,
        barcodes=barcodes,
    )

    assert len(
        result.groups
    ) == 1

    group = result.groups[0]

    assert (
        group.barcode_key
        == BARCODE
    )

    assert (
        group.document_count
        == 2
    )

    assert group.has_divergence


def test_same_line_should_not_create_candidate(
) -> None:
    first_document = uuid4()
    second_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
    ]

    elements = [
        *barcodes,
        create_normalized_line(
            document_id=first_document,
            value=LINE_A,
        ),
        create_normalized_line(
            document_id=second_document,
            value=LINE_A,
        ),
    ]

    result = select(
        elements=elements,
        barcodes=barcodes,
    )

    assert result.groups == ()


def test_repeated_same_line_inside_document_should_not_create_false_divergence(
) -> None:
    first_document = uuid4()
    second_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
    ]

    elements = [
        *barcodes,
        create_normalized_line(
            document_id=first_document,
            value=LINE_A,
        ),
        create_normalized_line(
            document_id=first_document,
            value=LINE_A,
        ),
        create_normalized_line(
            document_id=second_document,
            value=LINE_A,
        ),
    ]

    result = select(
        elements=elements,
        barcodes=barcodes,
    )

    assert result.groups == ()


def test_should_preserve_all_line_occurrence_ids(
) -> None:
    first_document = uuid4()
    second_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
    ]

    first_line = (
        create_normalized_line(
            document_id=first_document,
            value=LINE_A,
        )
    )

    duplicate_first_line = (
        create_normalized_line(
            document_id=first_document,
            value=LINE_A,
        )
    )

    second_line = (
        create_normalized_line(
            document_id=second_document,
            value=LINE_B,
        )
    )

    result = select(
        elements=[
            *barcodes,
            first_line,
            duplicate_first_line,
            second_line,
        ],
        barcodes=barcodes,
    )

    group = result.groups[0]

    first_candidate = next(
        document
        for document
        in group.documents
        if (
            document.document_id
            == first_document
        )
    )

    assert (
        first_candidate.numeric_line_values
        == (
            LINE_A,
        )
    )

    assert (
        set(
            first_candidate
            .numeric_line_element_ids
        )
        == {
            first_line.element_id,
            duplicate_first_line.element_id,
        }
    )


def test_document_without_line_should_remain_in_candidate_context(
) -> None:
    first_document = uuid4()
    second_document = uuid4()
    third_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
        create_barcode(
            document_id=third_document,
        ),
    ]

    result = select(
        elements=[
            *barcodes,
            create_normalized_line(
                document_id=first_document,
                value=LINE_A,
            ),
            create_normalized_line(
                document_id=second_document,
                value=LINE_B,
            ),
        ],
        barcodes=barcodes,
    )

    group = result.groups[0]

    assert (
        group.document_count
        == 3
    )

    assert (
        group.documents_with_numeric_lines
        == 2
    )

    third_candidate = next(
        document
        for document
        in group.documents
        if (
            document.document_id
            == third_document
        )
    )

    assert (
        third_candidate
        .numeric_line_values
        == ()
    )


def test_only_one_document_with_line_should_not_create_candidate(
) -> None:
    first_document = uuid4()
    second_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
    ]

    result = select(
        elements=[
            *barcodes,
            create_normalized_line(
                document_id=first_document,
                value=LINE_A,
            ),
        ],
        barcodes=barcodes,
    )

    assert result.groups == ()


def test_raw_line_should_not_participate_in_divergence(
) -> None:
    first_document = uuid4()
    second_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
    ]

    result = select(
        elements=[
            *barcodes,
            create_normalized_line(
                document_id=first_document,
                value=LINE_A,
            ),
            create_raw_line(
                document_id=second_document,
                value=LINE_B,
            ),
            create_normalized_line(
                document_id=second_document,
                value=LINE_A,
            ),
        ],
        barcodes=barcodes,
    )

    assert result.groups == ()


def test_should_build_candidate_statistics() -> None:
    first_document = uuid4()
    second_document = uuid4()
    third_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
        create_barcode(
            document_id=third_document,
        ),
    ]

    first_line = create_normalized_line(
        document_id=first_document,
        value=LINE_A,
    )

    second_line = create_normalized_line(
        document_id=second_document,
        value=LINE_B,
    )

    result = select(
        elements=[
            *barcodes,
            first_line,
            second_line,
        ],
        barcodes=barcodes,
    )

    assert (
        result.stats
        .source_groups_considered
        == 1
    )

    assert (
        result.stats.candidate_groups
        == 1
    )

    assert (
        result.stats.candidate_documents
        == 3
    )

    assert (
        result.stats.barcode_elements
        == 3
    )

    assert (
        result.stats.numeric_line_elements
        == 2
    )


def test_non_selected_source_index_should_be_ignored(
) -> None:
    first_document = uuid4()
    second_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
    ]

    result = select(
        elements=[
            *barcodes,
            create_normalized_line(
                document_id=first_document,
                value=LINE_A,
            ),
            create_normalized_line(
                document_id=second_document,
                value=LINE_B,
            ),
        ],
        barcodes=barcodes,
        source_indexes=[
            "qrcode"
        ],
    )

    assert result.groups == ()

    assert (
        result.stats
        .source_groups_considered
        == 0
    )


def test_candidate_group_should_not_materialize_pairs(
) -> None:
    first_document = uuid4()
    second_document = uuid4()

    barcodes = [
        create_barcode(
            document_id=first_document,
        ),
        create_barcode(
            document_id=second_document,
        ),
    ]

    result = select(
        elements=[
            *barcodes,
            create_normalized_line(
                document_id=first_document,
                value=LINE_A,
            ),
            create_normalized_line(
                document_id=second_document,
                value=LINE_B,
            ),
        ],
        barcodes=barcodes,
    )

    group = result.groups[0]

    assert not hasattr(
        group,
        "pairs",
    )


def test_should_reject_invalid_source_indexes_type(
) -> None:
    catalog = (
        ForensicElementCatalog()
    )

    registry = (
        ForensicIndexRegistry()
    )

    exact_candidates = (
        ExactCandidateSelectionEngine()
        .select(
            registry=registry,
            index_names=[],
        )
    )

    with pytest.raises(
        TypeError,
        match="source_indexes",
    ):
        (
            BarcodeNumericLineCandidateSelector()
            .select(
                catalog=catalog,
                exact_candidates=(
                    exact_candidates
                ),
                source_indexes="itf",  # type: ignore[arg-type]
            )
        )