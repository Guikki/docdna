from uuid import uuid4

import pytest

from app.domain.models.forensic_data_layer import (
    ForensicDataLayer,
)
from app.domain.models.forensic_element_type import (
    ForensicElementType,
)
from app.domain.models.numeric_line_validation import (
    NumericLineType,
    NumericLineValidation,
    NumericLineValidationStatus,
)
from app.domain.models.printed_numeric_line import (
    PrintedNumericLine,
)
from app.domain.services.canonical_forensic_index import (
    CanonicalForensicIndex,
)
from app.domain.services.forensic_canonicalizers import (
    canonicalize_digits,
)
from app.domain.services.forensic_element_catalog import (
    ForensicElementCatalog,
)
from app.domain.services.numeric_line_forensic_element_adapter import (
    NumericLineForensicElementAdapter,
)


NORMALIZED_LINE = (
    "00190500954014481606906809350314337370000000100"
)

RAW_LINE = (
    "00190.50095 "
    "40144.816069 "
    "06809.350314 "
    "3 "
    "37370000000100"
)


def create_line(
    *,
    line_index: int = 1,
    source: str = "native_text",
    raw_content: str = RAW_LINE,
    normalized_content: str = NORMALIZED_LINE,
) -> PrintedNumericLine:
    return PrintedNumericLine(
        line_index=line_index,
        source=source,
        raw_content=raw_content,
        normalized_content=(
            normalized_content
        ),
        digit_count=len(
            normalized_content
        ),
    )


def create_validation(
    *,
    line_index: int = 1,
    normalized_content: str = NORMALIZED_LINE,
    line_type: NumericLineType = (
        NumericLineType.BANK_SLIP
    ),
    status: NumericLineValidationStatus = (
        NumericLineValidationStatus.VALID
    ),
) -> NumericLineValidation:
    return NumericLineValidation(
        line_index=line_index,
        normalized_content=(
            normalized_content
        ),
        line_type=line_type,
        status=status,
        digit_count=len(
            normalized_content
        ),
        validation_method="modulo_10",
        valid_check_digits=3,
        total_check_digits=3,
        message=(
            "Linha digitável bancária "
            "estruturalmente válida."
        ),
    )


def test_should_create_three_elements_per_line() -> None:
    adapter = (
        NumericLineForensicElementAdapter()
    )

    elements = adapter.build(
        document_id=uuid4(),
        lines=[
            create_line()
        ],
        validations=[
            create_validation()
        ],
    )

    assert len(elements) == 3


def test_should_preserve_raw_occurrence() -> None:
    elements = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
        )
    )

    raw = elements[0]

    assert (
        raw.element_type
        is ForensicElementType.NUMERIC_LINE
    )

    assert (
        raw.subtype
        == "printed_numeric_line"
    )

    assert raw.value == RAW_LINE

    assert (
        raw.provenance.layer
        is ForensicDataLayer.EXTRACTED
    )

    assert (
        raw.metadata["source"]
        == "native_text"
    )


def test_should_create_normalized_child() -> None:
    elements = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
        )
    )

    raw = elements[0]
    normalized = elements[1]

    assert (
        normalized.subtype
        == "normalized_numeric_line"
    )

    assert (
        normalized.value
        == NORMALIZED_LINE
    )

    assert (
        normalized.provenance.layer
        is ForensicDataLayer.DERIVED
    )

    assert (
        normalized.parent_element_id
        == raw.element_id
    )


def test_should_create_validation_as_analytical_child() -> None:
    elements = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
        )
    )

    normalized = elements[1]
    validation = elements[2]

    assert (
        validation.subtype
        == "numeric_line_validation"
    )

    assert (
        validation.provenance.layer
        is ForensicDataLayer.ANALYTICAL
    )

    assert (
        validation.parent_element_id
        == normalized.element_id
    )


def test_should_preserve_validation_metadata() -> None:
    validation_element = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
        )[2]
    )

    assert (
        validation_element.metadata[
            "line_type"
        ]
        == "bank_slip"
    )

    assert (
        validation_element.metadata[
            "status"
        ]
        == "valid"
    )

    assert (
        validation_element.metadata[
            "validation_method"
        ]
        == "modulo_10"
    )

    assert (
        validation_element.metadata[
            "valid_check_digits"
        ]
        == 3
    )

    assert (
        validation_element.metadata[
            "total_check_digits"
        ]
        == 3
    )


def test_should_generate_deterministic_ids() -> None:
    document_id = uuid4()

    adapter = (
        NumericLineForensicElementAdapter()
    )

    first = adapter.build(
        document_id=document_id,
        lines=[
            create_line()
        ],
        validations=[
            create_validation()
        ],
    )

    second = adapter.build(
        document_id=document_id,
        lines=[
            create_line()
        ],
        validations=[
            create_validation()
        ],
    )

    assert [
        element.element_id
        for element in first
    ] == [
        element.element_id
        for element in second
    ]


def test_repeated_values_should_remain_distinct_occurrences() -> None:
    document_id = uuid4()

    elements = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=document_id,
            lines=[
                create_line(
                    line_index=1,
                    source="native_text",
                ),
                create_line(
                    line_index=2,
                    source="ocr",
                ),
            ],
            validations=[
                create_validation(
                    line_index=1,
                ),
                create_validation(
                    line_index=2,
                ),
            ],
        )
    )

    normalized = [
        element
        for element in elements
        if (
            element.subtype
            == "normalized_numeric_line"
        )
    ]

    assert len(normalized) == 2

    assert (
        normalized[0].value
        == normalized[1].value
    )

    assert (
        normalized[0].element_id
        != normalized[1].element_id
    )


def test_should_reject_count_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="quantidade de linhas",
    ):
        (
            NumericLineForensicElementAdapter()
            .build(
                document_id=uuid4(),
                lines=[
                    create_line()
                ],
                validations=[],
            )
        )


def test_should_reject_line_index_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="line_index",
    ):
        (
            NumericLineForensicElementAdapter()
            .build(
                document_id=uuid4(),
                lines=[
                    create_line(
                        line_index=1,
                    )
                ],
                validations=[
                    create_validation(
                        line_index=2,
                    )
                ],
            )
        )


def test_should_reject_normalized_content_mismatch() -> None:
    different_line = (
        "9" * 47
    )

    with pytest.raises(
        ValueError,
        match="conteúdo normalizado",
    ):
        (
            NumericLineForensicElementAdapter()
            .build(
                document_id=uuid4(),
                lines=[
                    create_line()
                ],
                validations=[
                    create_validation(
                        normalized_content=(
                            different_line
                        ),
                    )
                ],
            )
        )


def test_should_add_elements_to_catalog() -> None:
    elements = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
        )
    )

    catalog = (
        ForensicElementCatalog()
    )

    added = catalog.add_many(
        elements
    )

    assert added == 3

    assert len(
        catalog.by_type(
            ForensicElementType.NUMERIC_LINE
        )
    ) == 3


def test_canonical_index_should_group_same_line_across_documents(
) -> None:
    adapter = (
        NumericLineForensicElementAdapter()
    )

    first = adapter.build(
        document_id=uuid4(),
        lines=[
            create_line()
        ],
        validations=[
            create_validation()
        ],
    )

    second = adapter.build(
        document_id=uuid4(),
        lines=[
            create_line(
                raw_content=(
                    NORMALIZED_LINE
                ),
            )
        ],
        validations=[
            create_validation()
        ],
    )

    normalized_elements = [
        element
        for element in (
            first + second
        )
        if (
            element.subtype
            == "normalized_numeric_line"
        )
    ]

    index = CanonicalForensicIndex(
        key_type="numeric_line",
        element_type=(
            ForensicElementType.NUMERIC_LINE
        ),
        subtype=(
            "normalized_numeric_line"
        ),
        canonicalizer=(
            canonicalize_digits
        ),
    )

    index.add_many(
        normalized_elements
    )

    groups = (
        index.duplicate_groups(
            cross_document_only=True,
        )
    )

    assert len(groups) == 1

    assert (
        groups[0].element_count
        == 2
    )

    assert (
        groups[0]
        .cross_document_pairwise_relations
        == 1
    )


def test_same_line_repeated_inside_document_is_not_cross_document(
) -> None:
    document_id = uuid4()

    elements = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=document_id,
            lines=[
                create_line(
                    line_index=1,
                ),
                create_line(
                    line_index=2,
                ),
            ],
            validations=[
                create_validation(
                    line_index=1,
                ),
                create_validation(
                    line_index=2,
                ),
            ],
        )
    )

    normalized_elements = [
        element
        for element in elements
        if (
            element.subtype
            == "normalized_numeric_line"
        )
    ]

    index = CanonicalForensicIndex(
        key_type="numeric_line",
        element_type=(
            ForensicElementType.NUMERIC_LINE
        ),
        subtype=(
            "normalized_numeric_line"
        ),
        canonicalizer=(
            canonicalize_digits
        ),
    )

    index.add_many(
        normalized_elements
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