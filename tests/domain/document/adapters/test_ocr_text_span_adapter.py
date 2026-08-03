from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from app.domain.document.adapters.ocr_text_span_adapter import (
    OcrTextSpanAdapter,
)
from app.domain.document.models.color import Color
from app.domain.models.document_ocr import DocumentOcr
from app.domain.models.ocr_result import OcrResult
from app.domain.models.ocr_text_box import OcrTextBox


def create_document_ocr() -> DocumentOcr:
    return DocumentOcr(
        content="Texto OCR",
        character_count=9,
        pages_processed=2,
        pages_with_text=2,
        language="por",
    )


def create_text_box(
    *,
    page_number: int = 1,
    text: str = "Texto",
    confidence: float = 95.0,
    left: int = 10,
    top: int = 20,
    width: int = 100,
    height: int = 15,
) -> OcrTextBox:
    return OcrTextBox(
        page_number=page_number,
        text=text,
        confidence=confidence,
        left=left,
        top=top,
        width=width,
        height=height,
    )


def create_result(
    *,
    text_boxes: list[OcrTextBox] | None = None,
) -> OcrResult:
    return OcrResult(
        document_ocr=create_document_ocr(),
        text_boxes=(
            []
            if text_boxes is None
            else text_boxes
        ),
    )


def test_should_create_default_adapter() -> None:
    adapter = OcrTextSpanAdapter()

    assert adapter.font_name == "OCR_UNKNOWN"
    assert adapter.default_font_size == 1.0
    assert adapter.font_color == Color(
        red=0.0,
        green=0.0,
        blue=0.0,
    )


def test_should_normalize_font_name() -> None:
    adapter = OcrTextSpanAdapter(
        font_name="  OCR   Tesseract  ",
    )

    assert adapter.font_name == "OCR Tesseract"


@pytest.mark.parametrize(
    "font_name",
    [
        "",
        " ",
        "\t",
        "\n",
    ],
)
def test_should_reject_empty_font_name(
    font_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="font_name cannot be empty",
    ):
        OcrTextSpanAdapter(
            font_name=font_name,
        )


@pytest.mark.parametrize(
    "font_name",
    [
        None,
        123,
        True,
        [],
        {},
    ],
)
def test_should_reject_non_string_font_name(
    font_name: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="font_name must be a string",
    ):
        OcrTextSpanAdapter(
            font_name=font_name,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "default_font_size",
    [
        1,
        2.5,
        10,
        100,
    ],
)
def test_should_accept_positive_default_font_size(
    default_font_size: float,
) -> None:
    adapter = OcrTextSpanAdapter(
        default_font_size=default_font_size,
    )

    assert (
        adapter.default_font_size
        == float(default_font_size)
    )


@pytest.mark.parametrize(
    "default_font_size",
    [
        0,
        -1,
        -0.1,
    ],
)
def test_should_reject_non_positive_default_font_size(
    default_font_size: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be greater than zero",
    ):
        OcrTextSpanAdapter(
            default_font_size=default_font_size,
        )


@pytest.mark.parametrize(
    "default_font_size",
    [
        inf,
        -inf,
        nan,
    ],
)
def test_should_reject_non_finite_default_font_size(
    default_font_size: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be finite",
    ):
        OcrTextSpanAdapter(
            default_font_size=default_font_size,
        )


@pytest.mark.parametrize(
    "default_font_size",
    [
        True,
        False,
        "12",
        None,
        [],
    ],
)
def test_should_reject_non_numeric_default_font_size(
    default_font_size: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="must be numeric",
    ):
        OcrTextSpanAdapter(
            default_font_size=default_font_size,  # type: ignore[arg-type]
        )


def test_should_require_color_instance() -> None:
    with pytest.raises(
        TypeError,
        match="font_color must be a Color",
    ):
        OcrTextSpanAdapter(
            font_color="#000000",  # type: ignore[arg-type]
        )


def test_should_convert_empty_result() -> None:
    adapter = OcrTextSpanAdapter()

    spans = adapter.adapt(
        create_result()
    )

    assert spans == ()
    assert isinstance(spans, tuple)


def test_should_convert_single_text_box() -> None:
    adapter = OcrTextSpanAdapter()

    spans = adapter.adapt(
        create_result(
            text_boxes=[
                create_text_box(
                    page_number=2,
                    text="Valor total",
                    left=10,
                    top=20,
                    width=100,
                    height=15,
                )
            ]
        )
    )

    assert len(spans) == 1

    span = spans[0]

    assert span.text == "Valor total"
    assert span.page_number == 2

    assert span.bounding_box.left == 10.0
    assert span.bounding_box.top == 20.0
    assert span.bounding_box.right == 110.0
    assert span.bounding_box.bottom == 35.0

    assert span.font.name == "OCR_UNKNOWN"
    assert span.font.size == 15.0
    assert span.font.embedded is None


def test_should_preserve_original_text() -> None:
    adapter = OcrTextSpanAdapter()

    spans = adapter.adapt(
        create_result(
            text_boxes=[
                create_text_box(
                    text="  Texto   OCR  ",
                )
            ]
        )
    )

    assert spans[0].text == "  Texto   OCR  "
    assert (
        spans[0].normalized_text
        == "Texto OCR"
    )


def test_should_preserve_text_box_order() -> None:
    adapter = OcrTextSpanAdapter()

    result = create_result(
        text_boxes=[
            create_text_box(
                text="Primeiro",
            ),
            create_text_box(
                text="Segundo",
            ),
            create_text_box(
                text="Terceiro",
            ),
        ]
    )

    spans = adapter.adapt(result)

    assert tuple(
        span.text
        for span in spans
    ) == (
        "Primeiro",
        "Segundo",
        "Terceiro",
    )


def test_should_use_box_height_as_font_size() -> None:
    adapter = OcrTextSpanAdapter()

    span = adapter.adapt_box(
        create_text_box(
            height=27,
        )
    )

    assert span.font.size == 27.0


@pytest.mark.parametrize(
    "height",
    [
        0,
    ],
)
def test_should_use_default_font_size_for_non_positive_height(
    height: int,
) -> None:
    adapter = OcrTextSpanAdapter(
        default_font_size=2.5,
    )

    span = adapter.adapt_box(
        create_text_box(
            height=height,
        )
    )

    assert span.font.size == 2.5


def test_should_use_custom_technical_font() -> None:
    adapter = OcrTextSpanAdapter(
        font_name="Tesseract OCR",
        font_color=Color(
            red=0.2,
            green=0.3,
            blue=0.4,
        ),
    )

    span = adapter.adapt_box(
        create_text_box()
    )

    assert span.font.name == "Tesseract OCR"
    assert span.font.color == Color(
        red=0.2,
        green=0.3,
        blue=0.4,
    )


def test_should_not_copy_confidence_to_text_span() -> None:
    adapter = OcrTextSpanAdapter()

    span = adapter.adapt_box(
        create_text_box(
            confidence=42.5,
        )
    )

    assert not hasattr(
        span,
        "confidence",
    )


def test_should_not_modify_original_ocr_result() -> None:
    text_box = create_text_box(
        text="Texto",
        height=15,
    )

    result = create_result(
        text_boxes=[text_box]
    )

    adapter = OcrTextSpanAdapter()

    adapter.adapt(result)

    assert result.text_boxes == [
        text_box
    ]

    assert text_box.text == "Texto"
    assert text_box.height == 15


def test_should_group_spans_by_page() -> None:
    adapter = OcrTextSpanAdapter()

    result = create_result(
        text_boxes=[
            create_text_box(
                page_number=1,
                text="Página 1 - A",
            ),
            create_text_box(
                page_number=2,
                text="Página 2",
            ),
            create_text_box(
                page_number=1,
                text="Página 1 - B",
            ),
        ]
    )

    grouped = adapter.adapt_by_page(
        result
    )

    assert tuple(grouped) == (
        1,
        2,
    )

    assert tuple(
        span.text
        for span in grouped[1]
    ) == (
        "Página 1 - A",
        "Página 1 - B",
    )

    assert tuple(
        span.text
        for span in grouped[2]
    ) == (
        "Página 2",
    )


def test_adapt_by_page_should_return_tuples() -> None:
    adapter = OcrTextSpanAdapter()

    grouped = adapter.adapt_by_page(
        create_result(
            text_boxes=[
                create_text_box(),
            ]
        )
    )

    assert isinstance(
        grouped[1],
        tuple,
    )


def test_should_reject_invalid_result() -> None:
    adapter = OcrTextSpanAdapter()

    with pytest.raises(
        TypeError,
        match="must be an OcrResult",
    ):
        adapter.adapt(
            "invalid",  # type: ignore[arg-type]
        )


def test_should_reject_non_list_text_boxes() -> None:
    adapter = OcrTextSpanAdapter()

    result = OcrResult(
        document_ocr=create_document_ocr(),
        text_boxes=(),  # type: ignore[arg-type]
    )

    with pytest.raises(
        TypeError,
        match="text_boxes must be a list",
    ):
        adapter.adapt(result)


def test_should_reject_invalid_text_box_item() -> None:
    adapter = OcrTextSpanAdapter()

    result = OcrResult(
        document_ocr=create_document_ocr(),
        text_boxes=[
            "invalid",  # type: ignore[list-item]
        ],
    )

    with pytest.raises(
        TypeError,
        match=(
            "only OcrTextBox instances "
            "at index 0"
        ),
    ):
        adapter.adapt(result)


def test_should_report_invalid_text_box_index() -> None:
    adapter = OcrTextSpanAdapter()

    result = OcrResult(
        document_ocr=create_document_ocr(),
        text_boxes=[
            create_text_box(),
            "invalid",  # type: ignore[list-item]
        ],
    )

    with pytest.raises(
        TypeError,
        match=(
            "only OcrTextBox instances "
            "at index 1"
        ),
    ):
        adapter.adapt(result)


def test_should_reject_invalid_text_type() -> None:
    adapter = OcrTextSpanAdapter()

    text_box = create_text_box()
    object.__setattr__(
        text_box,
        "text",
        123,
    )

    with pytest.raises(
        TypeError,
        match="text must be a string",
    ):
        adapter.adapt_box(text_box)


@pytest.mark.parametrize(
    "page_number",
    [
        0,
        -1,
    ],
)
def test_should_reject_invalid_page_number(
    page_number: int,
) -> None:
    adapter = OcrTextSpanAdapter()

    with pytest.raises(
        ValueError,
        match=(
            "page_number must be greater than "
            "or equal to 1"
        ),
    ):
        adapter.adapt_box(
            create_text_box(
                page_number=page_number,
            )
        )


@pytest.mark.parametrize(
    "page_number",
    [
        True,
        1.0,
        "1",
        None,
    ],
)
def test_should_reject_non_integer_page_number(
    page_number: object,
) -> None:
    adapter = OcrTextSpanAdapter()

    text_box = create_text_box()

    object.__setattr__(
        text_box,
        "page_number",
        page_number,
    )

    with pytest.raises(
        TypeError,
        match=(
            "page_number must be an integer"
        ),
    ):
        adapter.adapt_box(text_box)


@pytest.mark.parametrize(
    "field_name",
    [
        "left",
        "top",
        "width",
        "height",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        True,
        1.5,
        "10",
        None,
    ],
)
def test_should_reject_non_integer_geometry(
    field_name: str,
    invalid_value: object,
) -> None:
    adapter = OcrTextSpanAdapter()

    text_box = create_text_box()

    object.__setattr__(
        text_box,
        field_name,
        invalid_value,
    )

    with pytest.raises(
        TypeError,
        match=(
            f"{field_name} must be an integer"
        ),
    ):
        adapter.adapt_box(text_box)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("width", -1),
        ("height", -1),
    ],
)
def test_should_reject_negative_dimensions(
    field_name: str,
    value: int,
) -> None:
    adapter = OcrTextSpanAdapter()

    text_box = create_text_box()

    object.__setattr__(
        text_box,
        field_name,
        value,
    )

    with pytest.raises(
        ValueError,
        match=(
            f"{field_name} cannot be negative"
        ),
    ):
        adapter.adapt_box(text_box)


@pytest.mark.parametrize(
    "confidence",
    [
        True,
        "95",
        None,
        [],
    ],
)
def test_should_reject_non_numeric_confidence(
    confidence: object,
) -> None:
    adapter = OcrTextSpanAdapter()

    text_box = create_text_box()

    object.__setattr__(
        text_box,
        "confidence",
        confidence,
    )

    with pytest.raises(
        TypeError,
        match=(
            "confidence must be a numeric value"
        ),
    ):
        adapter.adapt_box(text_box)


@pytest.mark.parametrize(
    "confidence",
    [
        inf,
        -inf,
        nan,
    ],
)
def test_should_reject_non_finite_confidence(
    confidence: float,
) -> None:
    adapter = OcrTextSpanAdapter()

    text_box = create_text_box()

    object.__setattr__(
        text_box,
        "confidence",
        confidence,
    )

    with pytest.raises(
        ValueError,
        match="confidence must be finite",
    ):
        adapter.adapt_box(text_box)


def test_should_allow_zero_area_box() -> None:
    adapter = OcrTextSpanAdapter()

    span = adapter.adapt_box(
        create_text_box(
            width=0,
            height=0,
        )
    )

    assert span.bounding_box.has_area is False
    assert span.font.size == 1.0


def test_should_allow_negative_position_coordinates() -> None:
    adapter = OcrTextSpanAdapter()

    span = adapter.adapt_box(
        create_text_box(
            left=-10,
            top=-20,
            width=100,
            height=15,
        )
    )

    assert span.bounding_box.left == -10.0
    assert span.bounding_box.top == -20.0


def test_should_be_immutable() -> None:
    adapter = OcrTextSpanAdapter()

    with pytest.raises(
        FrozenInstanceError,
    ):
        adapter.font_name = "Changed"  # type: ignore[misc]