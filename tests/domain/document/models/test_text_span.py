from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from app.domain.document.models.bounding_box import BoundingBox
from app.domain.document.models.color import Color
from app.domain.document.models.font import Font
from app.domain.document.models.text_span import TextSpan


def create_bounding_box() -> BoundingBox:
    return BoundingBox(
        left=10.0,
        top=20.0,
        right=110.0,
        bottom=40.0,
    )


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
    bounding_box: BoundingBox | None = None,
    font: Font | None = None,
    page_number: int = 1,
) -> TextSpan:
    return TextSpan(
        text=text,
        bounding_box=bounding_box or create_bounding_box(),
        font=font or create_font(),
        page_number=page_number,
    )


def test_should_create_text_span() -> None:
    bounding_box = create_bounding_box()
    font = create_font()

    span = TextSpan(
        text="Valor total: R$ 250,00",
        bounding_box=bounding_box,
        font=font,
        page_number=2,
    )

    assert span.text == "Valor total: R$ 250,00"
    assert span.bounding_box is bounding_box
    assert span.font is font
    assert span.page_number == 2


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        "\r\n",
        "Texto",
        "Texto com espaços",
        "Água",
        "你好",
        "🙂",
    ],
)
def test_should_accept_string_text(
    text: str,
) -> None:
    span = create_text_span(
        text=text,
    )

    assert span.text == text


@pytest.mark.parametrize(
    "text",
    [
        None,
        123,
        12.5,
        True,
        [],
        {},
        (),
        b"texto",
    ],
)
def test_should_reject_non_string_text(
    text: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="TextSpan text must be a string.",
    ):
        TextSpan(
            text=text,  # type: ignore[arg-type]
            bounding_box=create_bounding_box(),
            font=create_font(),
            page_number=1,
        )


def test_should_require_bounding_box_instance() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "TextSpan bounding_box must be a BoundingBox."
        ),
    ):
        TextSpan(
            text="Texto",
            bounding_box=(0, 0, 10, 10),  # type: ignore[arg-type]
            font=create_font(),
            page_number=1,
        )


@pytest.mark.parametrize(
    "bounding_box",
    [
        None,
        {},
        [],
        "0,0,10,10",
        123,
    ],
)
def test_should_reject_invalid_bounding_box(
    bounding_box: object,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "TextSpan bounding_box must be a BoundingBox."
        ),
    ):
        TextSpan(
            text="Texto",
            bounding_box=bounding_box,  # type: ignore[arg-type]
            font=create_font(),
            page_number=1,
        )


def test_should_require_font_instance() -> None:
    with pytest.raises(
        TypeError,
        match="TextSpan font must be a Font.",
    ):
        TextSpan(
            text="Texto",
            bounding_box=create_bounding_box(),
            font="Arial",  # type: ignore[arg-type]
            page_number=1,
        )


@pytest.mark.parametrize(
    "font",
    [
        None,
        {},
        [],
        "Arial",
        123,
    ],
)
def test_should_reject_invalid_font(
    font: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="TextSpan font must be a Font.",
    ):
        TextSpan(
            text="Texto",
            bounding_box=create_bounding_box(),
            font=font,  # type: ignore[arg-type]
            page_number=1,
        )


@pytest.mark.parametrize(
    "page_number",
    [
        1,
        2,
        10,
        100,
        999,
    ],
)
def test_should_accept_positive_page_number(
    page_number: int,
) -> None:
    span = create_text_span(
        page_number=page_number,
    )

    assert span.page_number == page_number


@pytest.mark.parametrize(
    "page_number",
    [
        0,
        -1,
        -10,
    ],
)
def test_should_reject_page_number_lower_than_one(
    page_number: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "TextSpan page_number must be greater than "
            "or equal to 1."
        ),
    ):
        create_text_span(
            page_number=page_number,
        )


@pytest.mark.parametrize(
    "page_number",
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
    page_number: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="TextSpan page_number must be an integer.",
    ):
        TextSpan(
            text="Texto",
            bounding_box=create_bounding_box(),
            font=create_font(),
            page_number=page_number,  # type: ignore[arg-type]
        )


def test_should_preserve_original_text() -> None:
    original_text = "  Valor   total \n da conta  "

    span = create_text_span(
        text=original_text,
    )

    assert span.text == original_text


def test_should_normalize_text_whitespace() -> None:
    span = create_text_span(
        text="  Valor   total \n da\tconta  ",
    )

    assert span.normalized_text == "Valor total da conta"


def test_should_apply_nfkc_unicode_normalization() -> None:
    span = create_text_span(
        text="Ｖａｌｏｒ　Ｔｏｔａｌ",
    )

    assert span.normalized_text == "Valor Total"


def test_should_preserve_accents_in_normalized_text() -> None:
    span = create_text_span(
        text="  Água   consumida  ",
    )

    assert span.normalized_text == "Água consumida"


def test_should_return_casefold_normalized_text() -> None:
    span = create_text_span(
        text="  VALOR   TOTAL  ",
    )

    assert span.normalized_casefold_text == "valor total"


def test_casefold_should_support_unicode_text() -> None:
    span = create_text_span(
        text="Straße",
    )

    assert span.normalized_casefold_text == "strasse"


@pytest.mark.parametrize(
    (
        "text",
        "expected_count",
    ),
    [
        ("", 0),
        ("A", 1),
        ("ABC", 3),
        ("A B", 3),
        ("  A  ", 5),
        ("\n", 1),
        ("Água", 4),
        ("🙂", 1),
    ],
)
def test_should_return_original_character_count(
    text: str,
    expected_count: int,
) -> None:
    span = create_text_span(
        text=text,
    )

    assert span.character_count == expected_count


@pytest.mark.parametrize(
    (
        "text",
        "expected_count",
    ),
    [
        ("", 0),
        ("   ", 0),
        ("A", 1),
        ("  A  ", 1),
        ("A   B", 3),
        ("  Valor   total  ", 11),
    ],
)
def test_should_return_normalized_character_count(
    text: str,
    expected_count: int,
) -> None:
    span = create_text_span(
        text=text,
    )

    assert span.normalized_character_count == expected_count


@pytest.mark.parametrize(
    (
        "text",
        "expected_count",
    ),
    [
        ("", 0),
        (" ", 0),
        ("   \n\t  ", 0),
        ("Texto", 1),
        ("Valor total", 2),
        ("  Valor   total  ", 2),
        ("Valor\ntotal\tda conta", 4),
        ("R$ 250,00", 2),
    ],
)
def test_should_return_word_count(
    text: str,
    expected_count: int,
) -> None:
    span = create_text_span(
        text=text,
    )

    assert span.word_count == expected_count


def test_should_identify_empty_text() -> None:
    span = create_text_span(
        text="",
    )

    assert span.is_empty is True
    assert span.is_whitespace is True
    assert span.has_visible_text is False


@pytest.mark.parametrize(
    "text",
    [
        " ",
        "   ",
        "\t",
        "\n",
        "\r\n",
        " \t\n ",
    ],
)
def test_should_identify_whitespace_text(
    text: str,
) -> None:
    span = create_text_span(
        text=text,
    )

    assert span.is_empty is False
    assert span.is_whitespace is True
    assert span.has_visible_text is False


@pytest.mark.parametrize(
    "text",
    [
        "A",
        " Texto ",
        "\nA\n",
        "0",
        ".",
        "Á",
        "🙂",
    ],
)
def test_should_identify_visible_text(
    text: str,
) -> None:
    span = create_text_span(
        text=text,
    )

    assert span.is_empty is False
    assert span.is_whitespace is False
    assert span.has_visible_text is True


def test_has_visible_text_should_not_analyze_font_color() -> None:
    transparent_font = Font(
        name="Arial",
        size=12.0,
        color=Color(
            red=0.0,
            green=0.0,
            blue=0.0,
            alpha=0.0,
        ),
    )

    span = create_text_span(
        text="Texto",
        font=transparent_font,
    )

    assert span.has_visible_text is True


def test_should_be_immutable() -> None:
    span = create_text_span()

    with pytest.raises(FrozenInstanceError):
        span.text = "Novo texto"  # type: ignore[misc]


def test_equal_text_spans_should_have_same_hash() -> None:
    first = create_text_span(
        text="Valor total",
        page_number=1,
    )
    second = create_text_span(
        text="Valor total",
        page_number=1,
    )

    assert first == second
    assert hash(first) == hash(second)


def test_text_spans_with_different_text_should_not_be_equal() -> None:
    first = create_text_span(
        text="Valor total",
    )
    second = create_text_span(
        text="Data de vencimento",
    )

    assert first != second


def test_text_spans_on_different_pages_should_not_be_equal() -> None:
    first = create_text_span(
        page_number=1,
    )
    second = create_text_span(
        page_number=2,
    )

    assert first != second


def test_text_spans_with_different_boxes_should_not_be_equal() -> None:
    first = create_text_span(
        bounding_box=BoundingBox(
            left=0,
            top=0,
            right=10,
            bottom=10,
        ),
    )
    second = create_text_span(
        bounding_box=BoundingBox(
            left=10,
            top=10,
            right=20,
            bottom=20,
        ),
    )

    assert first != second


def test_text_spans_with_different_fonts_should_not_be_equal() -> None:
    first = create_text_span(
        font=create_font(),
    )
    second = create_text_span(
        font=Font(
            name="Helvetica",
            size=12.0,
            color=Color(
                red=0.0,
                green=0.0,
                blue=0.0,
            ),
        ),
    )

    assert first != second