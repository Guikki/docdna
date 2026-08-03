from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.color import Color
from app.domain.document.models.document import Document
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
    text: str = "Texto",
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
    texts: tuple[str, ...] = (),
) -> Page:
    spans = tuple(
        create_text_span(
            text=text,
            page_number=number,
        )
        for text in texts
    )

    return Page(
        number=number,
        width=width,
        height=height,
        text_spans=spans,
    )


def create_document(
    *,
    pages: tuple[Page, ...] = (),
) -> Document:
    return Document(
        pages=pages,
    )


def test_should_create_empty_document() -> None:
    document = Document()

    assert document.pages == ()
    assert document.page_count == 0
    assert document.has_pages is False


def test_should_create_document_with_pages() -> None:
    first_page = create_page(
        number=1,
    )
    second_page = create_page(
        number=2,
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
        ),
    )

    assert document.pages == (
        first_page,
        second_page,
    )
    assert document.page_count == 2
    assert document.has_pages is True


@pytest.mark.parametrize(
    "pages",
    [
        [],
        {},
        set(),
        "pages",
        None,
    ],
)
def test_should_require_pages_tuple(
    pages: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="Document pages must be a tuple.",
    ):
        Document(
            pages=pages,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "invalid_item",
    [
        None,
        "Page",
        1,
        1.0,
        {},
        [],
        create_font(),
    ],
)
def test_should_reject_invalid_page_item(
    invalid_item: object,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "Document pages must contain only Page instances. "
            "Invalid item at index 0."
        ),
    ):
        create_document(
            pages=(
                invalid_item,  # type: ignore[arg-type]
            ),
        )


def test_should_report_invalid_page_item_index() -> None:
    valid_page = create_page(
        number=1,
    )

    with pytest.raises(
        TypeError,
        match=(
            "Document pages must contain only Page instances. "
            "Invalid item at index 1."
        ),
    ):
        create_document(
            pages=(
                valid_page,
                "invalid",  # type: ignore[arg-type]
            ),
        )


def test_should_reject_document_not_starting_at_page_one() -> None:
    page = create_page(
        number=2,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Document pages must use continuous numbering starting at 1. "
            "Expected page number 1 at index 0, received 2."
        ),
    ):
        create_document(
            pages=(page,),
        )


def test_should_reject_gap_in_page_numbers() -> None:
    first_page = create_page(
        number=1,
    )
    third_page = create_page(
        number=3,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Document pages must use continuous numbering starting at 1. "
            "Expected page number 2 at index 1, received 3."
        ),
    ):
        create_document(
            pages=(
                first_page,
                third_page,
            ),
        )


def test_should_reject_repeated_page_number() -> None:
    first_page = create_page(
        number=1,
    )
    repeated_page = create_page(
        number=1,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Document pages must use continuous numbering starting at 1. "
            "Expected page number 2 at index 1, received 1."
        ),
    ):
        create_document(
            pages=(
                first_page,
                repeated_page,
            ),
        )


def test_should_reject_pages_out_of_order() -> None:
    first_page = create_page(
        number=1,
    )
    third_page = create_page(
        number=3,
    )
    second_page = create_page(
        number=2,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Document pages must use continuous numbering starting at 1. "
            "Expected page number 2 at index 1, received 3."
        ),
    ):
        create_document(
            pages=(
                first_page,
                third_page,
                second_page,
            ),
        )


def test_should_accept_continuous_page_numbers() -> None:
    pages = tuple(
        create_page(
            number=number,
        )
        for number in range(1, 6)
    )

    document = create_document(
        pages=pages,
    )

    assert document.pages == pages
    assert document.page_numbers == (
        1,
        2,
        3,
        4,
        5,
    )


def test_empty_document_should_return_empty_page_numbers() -> None:
    document = create_document()

    assert document.page_numbers == ()


def test_should_preserve_page_order() -> None:
    first_page = create_page(
        number=1,
        texts=("Primeira",),
    )
    second_page = create_page(
        number=2,
        texts=("Segunda",),
    )
    third_page = create_page(
        number=3,
        texts=("Terceira",),
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
            third_page,
        ),
    )

    assert document.pages == (
        first_page,
        second_page,
        third_page,
    )
    assert document.page_numbers == (
        1,
        2,
        3,
    )


def test_empty_document_should_not_have_first_page() -> None:
    document = create_document()

    assert document.first_page is None


def test_should_return_first_page() -> None:
    first_page = create_page(
        number=1,
    )
    second_page = create_page(
        number=2,
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
        ),
    )

    assert document.first_page is first_page


def test_empty_document_should_not_have_last_page() -> None:
    document = create_document()

    assert document.last_page is None


def test_should_return_last_page() -> None:
    first_page = create_page(
        number=1,
    )
    second_page = create_page(
        number=2,
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
        ),
    )

    assert document.last_page is second_page


def test_empty_document_should_not_have_text_spans() -> None:
    document = create_document()

    assert document.has_text_spans is False
    assert document.text_span_count == 0


def test_document_with_empty_pages_should_not_have_text_spans() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
            ),
            create_page(
                number=2,
            ),
        ),
    )

    assert document.has_text_spans is False
    assert document.text_span_count == 0


def test_document_should_report_existing_text_spans() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
            ),
            create_page(
                number=2,
                texts=("Texto",),
            ),
        ),
    )

    assert document.has_text_spans is True
    assert document.text_span_count == 1


def test_document_with_empty_text_span_should_have_text_spans() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=("",),
            ),
        ),
    )

    assert document.has_text_spans is True
    assert document.has_visible_text is False
    assert document.text_span_count == 1


def test_empty_document_should_not_have_visible_text() -> None:
    document = create_document()

    assert document.has_visible_text is False


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
def test_document_with_whitespace_only_should_not_have_visible_text(
    text: str,
) -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=(text,),
            ),
        ),
    )

    assert document.has_visible_text is False


def test_document_should_have_visible_text_when_any_page_has_text() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=("   ",),
            ),
            create_page(
                number=2,
                texts=("Valor total",),
            ),
        ),
    )

    assert document.has_visible_text is True


def test_empty_document_should_return_empty_text() -> None:
    document = create_document()

    assert document.text == ""


def test_should_join_page_texts_with_two_line_breaks() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=(
                    "Nome",
                    "CPF",
                ),
            ),
            create_page(
                number=2,
                texts=(
                    "Valor",
                    "Vencimento",
                ),
            ),
        ),
    )

    assert document.text == (
        "Nome\nCPF\n\nValor\nVencimento"
    )


def test_original_document_text_should_preserve_span_content() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=(
                    "  Nome  ",
                    "CPF\t123",
                ),
            ),
        ),
    )

    assert document.text == (
        "  Nome  \nCPF\t123"
    )


def test_original_text_should_preserve_empty_pages() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=("Primeira",),
            ),
            create_page(
                number=2,
            ),
            create_page(
                number=3,
                texts=("Terceira",),
            ),
        ),
    )

    assert document.text == (
        "Primeira\n\n\n\nTerceira"
    )


def test_empty_document_should_return_empty_normalized_text() -> None:
    document = create_document()

    assert document.normalized_text == ""


def test_should_join_normalized_page_texts() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=(
                    "  Valor   total  ",
                    "Data\tde vencimento",
                ),
            ),
            create_page(
                number=2,
                texts=(
                    "  Código   do   cliente  ",
                ),
            ),
        ),
    )

    assert document.normalized_text == (
        "Valor total\nData de vencimento"
        "\n\n"
        "Código do cliente"
    )


def test_normalized_text_should_omit_empty_pages() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=("Primeira",),
            ),
            create_page(
                number=2,
                texts=("   ",),
            ),
            create_page(
                number=3,
            ),
            create_page(
                number=4,
                texts=("Quarta",),
            ),
        ),
    )

    assert document.normalized_text == (
        "Primeira\n\nQuarta"
    )


def test_should_sum_text_span_counts() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=(
                    "A",
                    "B",
                ),
            ),
            create_page(
                number=2,
                texts=(
                    "C",
                    "D",
                    "E",
                ),
            ),
        ),
    )

    assert document.text_span_count == 5


def test_should_sum_original_character_counts() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=(
                    "ABC",
                    " D ",
                ),
            ),
            create_page(
                number=2,
                texts=(
                    "EF",
                    "\n",
                ),
            ),
        ),
    )

    assert document.character_count == 9


def test_should_not_count_document_separators_as_characters() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=("A",),
            ),
            create_page(
                number=2,
                texts=("B",),
            ),
        ),
    )

    assert document.text == "A\n\nB"
    assert document.character_count == 2


def test_should_sum_normalized_character_counts() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=(
                    "  ABC  ",
                    "D   E",
                ),
            ),
            create_page(
                number=2,
                texts=(
                    " F ",
                    "   ",
                ),
            ),
        ),
    )

    assert document.normalized_character_count == 7


def test_should_not_count_normalized_separators_as_characters() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=("A",),
            ),
            create_page(
                number=2,
                texts=("B",),
            ),
        ),
    )

    assert document.normalized_text == "A\n\nB"
    assert document.normalized_character_count == 2


def test_should_sum_word_counts() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=(
                    "Valor total",
                    "Data de vencimento",
                ),
            ),
            create_page(
                number=2,
                texts=(
                    "Código do cliente",
                    "   ",
                ),
            ),
        ),
    )

    assert document.word_count == 8


def test_empty_document_should_have_zero_text_counts() -> None:
    document = create_document()

    assert document.text_span_count == 0
    assert document.character_count == 0
    assert document.normalized_character_count == 0
    assert document.word_count == 0


def test_empty_document_should_have_zero_total_area() -> None:
    document = create_document()

    assert document.total_area == 0.0


def test_should_sum_page_areas() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                width=100.0,
                height=200.0,
            ),
            create_page(
                number=2,
                width=300.0,
                height=400.0,
            ),
        ),
    )

    assert document.total_area == 140_000.0


def test_empty_document_should_not_have_largest_page() -> None:
    document = create_document()

    assert document.largest_page is None


def test_should_return_largest_page() -> None:
    first_page = create_page(
        number=1,
        width=100.0,
        height=100.0,
    )
    second_page = create_page(
        number=2,
        width=200.0,
        height=200.0,
    )
    third_page = create_page(
        number=3,
        width=150.0,
        height=150.0,
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
            third_page,
        ),
    )

    assert document.largest_page is second_page


def test_largest_page_should_return_first_page_on_tie() -> None:
    first_page = create_page(
        number=1,
        width=100.0,
        height=200.0,
    )
    second_page = create_page(
        number=2,
        width=200.0,
        height=100.0,
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
        ),
    )

    assert document.largest_page is first_page


def test_empty_document_should_not_have_smallest_page() -> None:
    document = create_document()

    assert document.smallest_page is None


def test_should_return_smallest_page() -> None:
    first_page = create_page(
        number=1,
        width=100.0,
        height=100.0,
    )
    second_page = create_page(
        number=2,
        width=200.0,
        height=200.0,
    )
    third_page = create_page(
        number=3,
        width=150.0,
        height=150.0,
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
            third_page,
        ),
    )

    assert document.smallest_page is first_page


def test_smallest_page_should_return_first_page_on_tie() -> None:
    first_page = create_page(
        number=1,
        width=100.0,
        height=200.0,
    )
    second_page = create_page(
        number=2,
        width=200.0,
        height=100.0,
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
        ),
    )

    assert document.smallest_page is first_page


def test_empty_document_should_have_zero_average_page_area() -> None:
    document = create_document()

    assert document.average_page_area == 0.0


def test_should_calculate_average_page_area() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                width=100.0,
                height=100.0,
            ),
            create_page(
                number=2,
                width=200.0,
                height=100.0,
            ),
            create_page(
                number=3,
                width=300.0,
                height=100.0,
            ),
        ),
    )

    assert document.average_page_area == 20_000.0


def test_should_return_pages_with_text_spans() -> None:
    first_page = create_page(
        number=1,
    )
    second_page = create_page(
        number=2,
        texts=("",),
    )
    third_page = create_page(
        number=3,
        texts=("Texto",),
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
            third_page,
        ),
    )

    assert document.pages_with_text_spans() == (
        second_page,
        third_page,
    )


def test_pages_with_text_spans_should_return_tuple() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=("Texto",),
            ),
        ),
    )

    result = document.pages_with_text_spans()

    assert isinstance(result, tuple)


def test_should_return_pages_with_visible_text() -> None:
    first_page = create_page(
        number=1,
    )
    second_page = create_page(
        number=2,
        texts=("   ",),
    )
    third_page = create_page(
        number=3,
        texts=("Texto",),
    )
    fourth_page = create_page(
        number=4,
        texts=("Outro texto",),
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
            third_page,
            fourth_page,
        ),
    )

    assert document.pages_with_visible_text() == (
        third_page,
        fourth_page,
    )


def test_pages_with_visible_text_should_return_tuple() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
                texts=("Texto",),
            ),
        ),
    )

    result = document.pages_with_visible_text()

    assert isinstance(result, tuple)


def test_should_return_page_by_number() -> None:
    first_page = create_page(
        number=1,
    )
    second_page = create_page(
        number=2,
    )
    third_page = create_page(
        number=3,
    )

    document = create_document(
        pages=(
            first_page,
            second_page,
            third_page,
        ),
    )

    assert document.page_by_number(1) is first_page
    assert document.page_by_number(2) is second_page
    assert document.page_by_number(3) is third_page


@pytest.mark.parametrize(
    "number",
    [
        1,
        2,
        10,
        100,
    ],
)
def test_empty_document_should_return_none_for_valid_page_number(
    number: int,
) -> None:
    document = create_document()

    assert document.page_by_number(number) is None


def test_should_return_none_for_page_number_above_page_count() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
            ),
            create_page(
                number=2,
            ),
        ),
    )

    assert document.page_by_number(3) is None
    assert document.page_by_number(100) is None


@pytest.mark.parametrize(
    "number",
    [
        0,
        -1,
        -10,
    ],
)
def test_page_by_number_should_reject_number_lower_than_one(
    number: int,
) -> None:
    document = create_document()

    with pytest.raises(
        ValueError,
        match=(
            "Requested page number must be greater than or equal to 1."
        ),
    ):
        document.page_by_number(number)


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
def test_page_by_number_should_reject_non_integer_number(
    number: object,
) -> None:
    document = create_document()

    with pytest.raises(
        TypeError,
        match="Requested page number must be an integer.",
    ):
        document.page_by_number(
            number,  # type: ignore[arg-type]
        )


def test_should_be_immutable() -> None:
    document = create_document()

    with pytest.raises(FrozenInstanceError):
        document.pages = ()  # type: ignore[misc]


def test_pages_tuple_should_not_be_mutable() -> None:
    document = create_document(
        pages=(
            create_page(
                number=1,
            ),
        ),
    )

    with pytest.raises(AttributeError):
        document.pages.append(  # type: ignore[attr-defined]
            create_page(
                number=2,
            )
        )


def test_equal_documents_should_have_same_hash() -> None:
    first = create_document(
        pages=(
            create_page(
                number=1,
                texts=("Texto",),
            ),
        ),
    )
    second = create_document(
        pages=(
            create_page(
                number=1,
                texts=("Texto",),
            ),
        ),
    )

    assert first == second
    assert hash(first) == hash(second)


def test_documents_with_different_page_counts_should_not_be_equal() -> None:
    first = create_document(
        pages=(
            create_page(
                number=1,
            ),
        ),
    )
    second = create_document(
        pages=(
            create_page(
                number=1,
            ),
            create_page(
                number=2,
            ),
        ),
    )

    assert first != second


def test_documents_with_different_page_contents_should_not_be_equal() -> None:
    first = create_document(
        pages=(
            create_page(
                number=1,
                texts=("Valor",),
            ),
        ),
    )
    second = create_document(
        pages=(
            create_page(
                number=1,
                texts=("Vencimento",),
            ),
        ),
    )

    assert first != second


def test_documents_with_different_page_dimensions_should_not_be_equal() -> None:
    first = create_document(
        pages=(
            create_page(
                number=1,
                width=595.0,
                height=842.0,
            ),
        ),
    )
    second = create_document(
        pages=(
            create_page(
                number=1,
                width=600.0,
                height=842.0,
            ),
        ),
    )

    assert first != second