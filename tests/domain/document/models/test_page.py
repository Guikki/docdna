from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.color import Color
from app.domain.document.models.font import Font
from app.domain.document.models.page import Page
from app.domain.document.models.text_span import TextSpan


def create_font() -> Font:
    return Font(
        name="Arial",
        size=12.0,
        color=Color(
            red=0.0,
            green=0.0,
            blue=0.0,
        ),
    )


def create_text_span(
    *,
    text: str = "Valor total",
    page_number: int = 1,
    left: float = 10.0,
    top: float = 20.0,
    right: float = 110.0,
    bottom: float = 40.0,
) -> TextSpan:
    return TextSpan(
        text=text,
        bounding_box=BoundingBox(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        ),
        font=create_font(),
        page_number=page_number,
    )


def create_page(
    *,
    number: int = 1,
    width: float = 595.0,
    height: float = 842.0,
    text_spans: tuple[TextSpan, ...] = (),
) -> Page:
    return Page(
        number=number,
        width=width,
        height=height,
        text_spans=text_spans,
    )


def test_should_create_empty_page() -> None:
    page = Page(
        number=1,
        width=595,
        height=842,
    )

    assert page.number == 1
    assert page.width == 595.0
    assert page.height == 842.0
    assert page.text_spans == ()


def test_should_create_page_with_text_spans() -> None:
    first_span = create_text_span(
        text="Nome",
    )
    second_span = create_text_span(
        text="Documento",
    )

    page = create_page(
        text_spans=(
            first_span,
            second_span,
        ),
    )

    assert page.text_spans == (
        first_span,
        second_span,
    )
    assert page.text_span_count == 2


@pytest.mark.parametrize(
    "number",
    [
        1,
        2,
        10,
        100,
        999,
    ],
)
def test_should_accept_positive_page_number(
    number: int,
) -> None:
    page = create_page(
        number=number,
    )

    assert page.number == number


@pytest.mark.parametrize(
    "number",
    [
        0,
        -1,
        -10,
    ],
)
def test_should_reject_page_number_lower_than_one(
    number: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Page number must be greater than or equal to 1."
        ),
    ):
        create_page(
            number=number,
        )


@pytest.mark.parametrize(
    "number",
    [
        True,
        False,
        1.0,
        2.5,
        "1",
        None,
        [],
        {},
    ],
)
def test_should_reject_non_integer_page_number(
    number: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="Page number must be an integer.",
    ):
        Page(
            number=number,  # type: ignore[arg-type]
            width=595.0,
            height=842.0,
        )


@pytest.mark.parametrize(
    "width",
    [
        1,
        100,
        595,
        595.5,
        1000.25,
    ],
)
def test_should_accept_positive_width(
    width: float,
) -> None:
    page = create_page(
        width=width,
    )

    assert page.width == float(width)


@pytest.mark.parametrize(
    "height",
    [
        1,
        100,
        842,
        842.5,
        1000.25,
    ],
)
def test_should_accept_positive_height(
    height: float,
) -> None:
    page = create_page(
        height=height,
    )

    assert page.height == float(height)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("width", 0),
        ("width", 0.0),
        ("width", -1),
        ("width", -0.1),
        ("height", 0),
        ("height", 0.0),
        ("height", -1),
        ("height", -0.1),
    ],
)
def test_should_reject_non_positive_dimensions(
    field_name: str,
    value: float,
) -> None:
    arguments = {
        "number": 1,
        "width": 595.0,
        "height": 842.0,
        field_name: value,
    }

    with pytest.raises(
        ValueError,
        match=f"Page {field_name} must be greater than zero.",
    ):
        Page(**arguments)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("width", inf),
        ("width", -inf),
        ("width", nan),
        ("height", inf),
        ("height", -inf),
        ("height", nan),
    ],
)
def test_should_reject_non_finite_dimensions(
    field_name: str,
    value: float,
) -> None:
    arguments = {
        "number": 1,
        "width": 595.0,
        "height": 842.0,
        field_name: value,
    }

    with pytest.raises(
        ValueError,
        match=f"Page {field_name} must be finite.",
    ):
        Page(**arguments)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("width", True),
        ("width", False),
        ("width", "595"),
        ("width", None),
        ("width", []),
        ("height", True),
        ("height", False),
        ("height", "842"),
        ("height", None),
        ("height", {}),
    ],
)
def test_should_reject_non_numeric_dimensions(
    field_name: str,
    value: object,
) -> None:
    arguments = {
        "number": 1,
        "width": 595.0,
        "height": 842.0,
        field_name: value,
    }

    with pytest.raises(
        TypeError,
        match=f"Page {field_name} must be a numeric value.",
    ):
        Page(**arguments)


@pytest.mark.parametrize(
    "text_spans",
    [
        [],
        {},
        set(),
        "span",
        None,
    ],
)
def test_should_require_text_spans_tuple(
    text_spans: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="Page text_spans must be a tuple.",
    ):
        Page(
            number=1,
            width=595.0,
            height=842.0,
            text_spans=text_spans,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "invalid_item",
    [
        None,
        "Texto",
        123,
        {},
        [],
        create_font(),
    ],
)
def test_should_reject_invalid_text_span_item(
    invalid_item: object,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "Page text_spans must contain only TextSpan "
            "instances. Invalid item at index 0."
        ),
    ):
        create_page(
            text_spans=(
                invalid_item,  # type: ignore[arg-type]
            ),
        )


def test_should_report_invalid_text_span_index() -> None:
    valid_span = create_text_span()

    with pytest.raises(
        TypeError,
        match=(
            "Page text_spans must contain only TextSpan "
            "instances. Invalid item at index 1."
        ),
    ):
        create_page(
            text_spans=(
                valid_span,
                "invalid",  # type: ignore[arg-type]
            ),
        )


def test_should_reject_span_from_different_page() -> None:
    span = create_text_span(
        page_number=2,
    )

    with pytest.raises(
        ValueError,
        match=(
            "TextSpan page_number must match the containing "
            "Page number. Invalid item at index 0."
        ),
    ):
        create_page(
            number=1,
            text_spans=(span,),
        )


def test_should_accept_spans_matching_page_number() -> None:
    first_span = create_text_span(
        page_number=3,
        text="Primeiro",
    )
    second_span = create_text_span(
        page_number=3,
        text="Segundo",
    )

    page = create_page(
        number=3,
        text_spans=(
            first_span,
            second_span,
        ),
    )

    assert page.number == 3
    assert page.text_spans == (
        first_span,
        second_span,
    )


def test_should_calculate_area() -> None:
    page = create_page(
        width=100.0,
        height=200.0,
    )

    assert page.area == 20_000.0


def test_should_calculate_aspect_ratio() -> None:
    page = create_page(
        width=200.0,
        height=100.0,
    )

    assert page.aspect_ratio == 2.0


def test_should_return_complete_page_box() -> None:
    page = create_page(
        width=595.0,
        height=842.0,
    )

    assert page.page_box == BoundingBox(
        left=0.0,
        top=0.0,
        right=595.0,
        bottom=842.0,
    )


def test_empty_page_should_not_have_text_spans() -> None:
    page = create_page()

    assert page.text_span_count == 0
    assert page.has_text_spans is False


def test_page_should_report_existing_text_spans() -> None:
    page = create_page(
        text_spans=(
            create_text_span(),
        ),
    )

    assert page.text_span_count == 1
    assert page.has_text_spans is True


def test_page_with_empty_span_should_have_text_span() -> None:
    page = create_page(
        text_spans=(
            create_text_span(
                text="",
            ),
        ),
    )

    assert page.has_text_spans is True
    assert page.has_visible_text is False


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        "\r\n",
    ],
)
def test_page_with_only_whitespace_should_not_have_visible_text(
    text: str,
) -> None:
    page = create_page(
        text_spans=(
            create_text_span(
                text=text,
            ),
        ),
    )

    assert page.has_text_spans is True
    assert page.has_visible_text is False


def test_page_should_have_visible_text_when_any_span_is_visible() -> None:
    page = create_page(
        text_spans=(
            create_text_span(
                text="   ",
            ),
            create_text_span(
                text="Valor",
            ),
        ),
    )

    assert page.has_visible_text is True


def test_should_join_original_span_texts_with_line_breaks() -> None:
    page = create_page(
        text_spans=(
            create_text_span(
                text="  Nome  ",
            ),
            create_text_span(
                text="CPF",
            ),
            create_text_span(
                text="",
            ),
        ),
    )

    assert page.text == "  Nome  \nCPF\n"


def test_empty_page_should_return_empty_text() -> None:
    page = create_page()

    assert page.text == ""


def test_should_join_normalized_non_empty_texts() -> None:
    page = create_page(
        text_spans=(
            create_text_span(
                text="  Valor   total  ",
            ),
            create_text_span(
                text="  ",
            ),
            create_text_span(
                text="Data\tde\nvencimento",
            ),
        ),
    )

    assert page.normalized_text == (
        "Valor total\nData de vencimento"
    )


def test_empty_page_should_return_empty_normalized_text() -> None:
    page = create_page()

    assert page.normalized_text == ""


def test_should_sum_original_character_counts() -> None:
    page = create_page(
        text_spans=(
            create_text_span(
                text="ABC",
            ),
            create_text_span(
                text="  D  ",
            ),
            create_text_span(
                text="\n",
            ),
        ),
    )

    assert page.character_count == 9


def test_should_sum_normalized_character_counts() -> None:
    page = create_page(
        text_spans=(
            create_text_span(
                text="  ABC  ",
            ),
            create_text_span(
                text="D   E",
            ),
            create_text_span(
                text="   ",
            ),
        ),
    )

    assert page.normalized_character_count == 6


def test_should_sum_word_counts() -> None:
    page = create_page(
        text_spans=(
            create_text_span(
                text="Valor total",
            ),
            create_text_span(
                text="Data de vencimento",
            ),
            create_text_span(
                text="   ",
            ),
        ),
    )

    assert page.word_count == 5


def test_empty_page_should_have_zero_text_counts() -> None:
    page = create_page()

    assert page.character_count == 0
    assert page.normalized_character_count == 0
    assert page.word_count == 0


def test_empty_page_should_not_have_text_bounding_box() -> None:
    page = create_page()

    assert page.text_bounding_box is None


def test_should_return_single_span_bounding_box() -> None:
    span = create_text_span(
        left=10.0,
        top=20.0,
        right=110.0,
        bottom=40.0,
    )

    page = create_page(
        text_spans=(span,),
    )

    assert page.text_bounding_box == span.bounding_box


def test_should_calculate_combined_text_bounding_box() -> None:
    first_span = create_text_span(
        text="Primeiro",
        left=50.0,
        top=20.0,
        right=150.0,
        bottom=40.0,
    )
    second_span = create_text_span(
        text="Segundo",
        left=10.0,
        top=100.0,
        right=90.0,
        bottom=130.0,
    )
    third_span = create_text_span(
        text="Terceiro",
        left=70.0,
        top=5.0,
        right=200.0,
        bottom=80.0,
    )

    page = create_page(
        text_spans=(
            first_span,
            second_span,
            third_span,
        ),
    )

    assert page.text_bounding_box == BoundingBox(
        left=10.0,
        top=5.0,
        right=200.0,
        bottom=130.0,
    )


def test_text_bounding_box_should_include_whitespace_spans() -> None:
    whitespace_span = create_text_span(
        text="   ",
        left=5.0,
        top=5.0,
        right=20.0,
        bottom=20.0,
    )
    visible_span = create_text_span(
        text="Texto",
        left=100.0,
        top=100.0,
        right=150.0,
        bottom=120.0,
    )

    page = create_page(
        text_spans=(
            whitespace_span,
            visible_span,
        ),
    )

    assert page.text_bounding_box == BoundingBox(
        left=5.0,
        top=5.0,
        right=150.0,
        bottom=120.0,
    )


def test_should_return_only_spans_with_visible_text() -> None:
    empty_span = create_text_span(
        text="",
    )
    whitespace_span = create_text_span(
        text="   ",
    )
    first_visible_span = create_text_span(
        text="Nome",
    )
    second_visible_span = create_text_span(
        text="CPF",
    )

    page = create_page(
        text_spans=(
            empty_span,
            first_visible_span,
            whitespace_span,
            second_visible_span,
        ),
    )

    assert page.spans_with_visible_text() == (
        first_visible_span,
        second_visible_span,
    )


def test_spans_with_visible_text_should_return_tuple() -> None:
    page = create_page(
        text_spans=(
            create_text_span(
                text="Texto",
            ),
        ),
    )

    result = page.spans_with_visible_text()

    assert isinstance(result, tuple)


def test_should_preserve_text_span_order() -> None:
    first_span = create_text_span(
        text="Primeiro",
    )
    second_span = create_text_span(
        text="Segundo",
    )
    third_span = create_text_span(
        text="Terceiro",
    )

    page = create_page(
        text_spans=(
            first_span,
            second_span,
            third_span,
        ),
    )

    assert page.text_spans == (
        first_span,
        second_span,
        third_span,
    )
    assert page.text == "Primeiro\nSegundo\nTerceiro"


def test_should_be_immutable() -> None:
    page = create_page()

    with pytest.raises(FrozenInstanceError):
        page.number = 2  # type: ignore[misc]


def test_text_spans_tuple_should_not_be_mutable() -> None:
    page = create_page(
        text_spans=(
            create_text_span(),
        ),
    )

    with pytest.raises(AttributeError):
        page.text_spans.append(  # type: ignore[attr-defined]
            create_text_span()
        )


def test_equal_pages_should_have_same_hash() -> None:
    first = create_page(
        text_spans=(
            create_text_span(
                text="Valor",
            ),
        ),
    )
    second = create_page(
        text_spans=(
            create_text_span(
                text="Valor",
            ),
        ),
    )

    assert first == second
    assert hash(first) == hash(second)


def test_pages_with_different_numbers_should_not_be_equal() -> None:
    first = create_page(
        number=1,
    )
    second = create_page(
        number=2,
    )

    assert first != second


def test_pages_with_different_dimensions_should_not_be_equal() -> None:
    first = create_page(
        width=595.0,
        height=842.0,
    )
    second = create_page(
        width=600.0,
        height=842.0,
    )

    assert first != second


def test_pages_with_different_spans_should_not_be_equal() -> None:
    first = create_page(
        text_spans=(
            create_text_span(
                text="Valor",
            ),
        ),
    )
    second = create_page(
        text_spans=(
            create_text_span(
                text="Vencimento",
            ),
        ),
    )

    assert first != second