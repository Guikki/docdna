from uuid import uuid4

import pytest

from app.domain.models.forensic_data_layer import (
    ForensicDataLayer,
)
from app.domain.models.forensic_element_type import (
    ForensicElementType,
)
from app.domain.models.numeric_line_location import (
    NumericLineLocation,
)
from app.domain.models.numeric_line_validation import (
    NumericLineType,
    NumericLineValidation,
    NumericLineValidationStatus,
)
from app.domain.models.printed_numeric_line import (
    PrintedNumericLine,
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
) -> PrintedNumericLine:
    return PrintedNumericLine(
        line_index=line_index,
        source="ocr",
        raw_content=RAW_LINE,
        normalized_content=(
            NORMALIZED_LINE
        ),
        digit_count=47,
    )


def create_validation(
    *,
    line_index: int = 1,
) -> NumericLineValidation:
    return NumericLineValidation(
        line_index=line_index,
        normalized_content=(
            NORMALIZED_LINE
        ),
        line_type=(
            NumericLineType.BANK_SLIP
        ),
        status=(
            NumericLineValidationStatus.VALID
        ),
        digit_count=47,
        validation_method="modulo_10",
        valid_check_digits=3,
        total_check_digits=3,
        message="Linha válida.",
    )


def create_location(
    *,
    line_index: int = 1,
    page_number: int | None = 2,
    located: bool = True,
) -> NumericLineLocation:
    return NumericLineLocation(
        line_index=line_index,
        page_number=page_number,
        matched_content=(
            NORMALIZED_LINE
            if located
            else None
        ),
        left=(
            100
            if located
            else None
        ),
        top=(
            200
            if located
            else None
        ),
        width=(
            800
            if located
            else None
        ),
        height=(
            70
            if located
            else None
        ),
        confidence=(
            92.5
            if located
            else None
        ),
        source_image_path=(
            "storage/page_2.png"
            if located
            else None
        ),
        annotated_image_path=(
            "storage/page_2_line_1.png"
            if located
            else None
        ),
        located=located,
        message=(
            "Linha localizada."
            if located
            else "Linha não localizada."
        ),
    )


def test_should_create_location_element() -> None:
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
            locations=[
                create_location()
            ],
        )
    )

    assert len(elements) == 4

    location = elements[3]

    assert (
        location.element_type
        is ForensicElementType.LOCATION
    )

    assert (
        location.subtype
        == "numeric_line_location"
    )


def test_location_should_be_child_of_raw_occurrence() -> None:
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
            locations=[
                create_location()
            ],
        )
    )

    raw = elements[0]
    location = elements[3]

    assert (
        location.parent_element_id
        == raw.element_id
    )


def test_location_should_preserve_page() -> None:
    location = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
            locations=[
                create_location(
                    page_number=7,
                )
            ],
        )[3]
    )

    assert location.page_number == 7


def test_location_should_preserve_coordinates() -> None:
    location = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
            locations=[
                create_location()
            ],
        )[3]
    )

    assert (
        location.metadata["left"]
        == 100
    )

    assert (
        location.metadata["top"]
        == 200
    )

    assert (
        location.metadata["width"]
        == 800
    )

    assert (
        location.metadata["height"]
        == 70
    )


def test_location_should_preserve_confidence() -> None:
    location = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
            locations=[
                create_location()
            ],
        )[3]
    )

    assert (
        location.metadata[
            "confidence"
        ]
        == 92.5
    )


def test_should_use_annotated_image_as_content_reference() -> None:
    location = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
            locations=[
                create_location()
            ],
        )[3]
    )

    assert (
        location.content_ref
        == "storage/page_2_line_1.png"
    )


def test_not_located_result_should_also_be_preserved() -> None:
    location = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
            locations=[
                create_location(
                    located=False,
                    page_number=None,
                )
            ],
        )[3]
    )

    assert (
        location.metadata["located"]
        is False
    )

    assert location.page_number is None

    assert (
        location.metadata["message"]
        == "Linha não localizada."
    )


def test_location_should_be_derived_data() -> None:
    location = (
        NumericLineForensicElementAdapter()
        .build(
            document_id=uuid4(),
            lines=[
                create_line()
            ],
            validations=[
                create_validation()
            ],
            locations=[
                create_location()
            ],
        )[3]
    )

    assert (
        location.provenance.layer
        is ForensicDataLayer.DERIVED
    )

    assert (
        location.provenance.producer
        == "NumericLineVisualEvidenceBuilder"
    )


def test_should_reject_location_count_mismatch() -> None:
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
                validations=[
                    create_validation()
                ],
                locations=[],
            )
        )


def test_should_reject_location_line_index_mismatch() -> None:
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
                        line_index=1,
                    )
                ],
                locations=[
                    create_location(
                        line_index=2,
                    )
                ],
            )
        )


def test_location_identity_should_be_deterministic() -> None:
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
        locations=[
            create_location()
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
        locations=[
            create_location()
        ],
    )

    assert (
        first[3].element_id
        == second[3].element_id
    )