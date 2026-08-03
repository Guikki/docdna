from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from app.domain.document.models.color import Color
from app.domain.document.models.font import Font


def create_color() -> Color:
    return Color(
        red=0.1,
        green=0.2,
        blue=0.3,
    )


def create_font(
    *,
    name: str = "Arial",
    size: float = 12.0,
    color: Color | None = None,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    monospaced: bool = False,
    embedded: bool | None = None,
) -> Font:
    return Font(
        name=name,
        size=size,
        color=color or create_color(),
        bold=bold,
        italic=italic,
        underline=underline,
        monospaced=monospaced,
        embedded=embedded,
    )


def test_should_create_font() -> None:
    color = create_color()

    font = Font(
        name="Arial",
        size=12,
        color=color,
        bold=True,
        italic=False,
        underline=False,
        monospaced=False,
        embedded=True,
    )

    assert font.name == "Arial"
    assert font.size == 12.0
    assert font.color is color
    assert font.bold is True
    assert font.italic is False
    assert font.underline is False
    assert font.monospaced is False
    assert font.embedded is True


def test_should_normalize_font_name_whitespace() -> None:
    font = create_font(
        name="  Times   New \n Roman  ",
    )

    assert font.name == "Times New Roman"


def test_should_apply_unicode_nfkc_normalization_to_name() -> None:
    font = create_font(
        name="Ａｒｉａｌ",
    )

    assert font.name == "Arial"


def test_should_return_comparison_friendly_normalized_name() -> None:
    font = create_font(
        name="  TIMES   New Roman ",
    )

    assert font.normalized_name == "times new roman"


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        "\t",
        "\n",
        "   \t\n   ",
    ],
)
def test_should_reject_empty_font_name(
    name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Font name cannot be empty.",
    ):
        create_font(
            name=name,
        )


@pytest.mark.parametrize(
    "name",
    [
        None,
        123,
        12.5,
        True,
        [],
        {},
    ],
)
def test_should_reject_non_string_font_name(
    name: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="Font name must be a string.",
    ):
        Font(
            name=name,  # type: ignore[arg-type]
            size=12.0,
            color=create_color(),
        )


@pytest.mark.parametrize(
    "size",
    [
        1,
        8,
        10.5,
        72,
    ],
)
def test_should_accept_positive_numeric_size(
    size: float,
) -> None:
    font = create_font(
        size=size,
    )

    assert font.size == float(size)


@pytest.mark.parametrize(
    "size",
    [
        0,
        0.0,
        -0.1,
        -1,
        -12.5,
    ],
)
def test_should_reject_non_positive_size(
    size: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Font size must be greater than zero.",
    ):
        create_font(
            size=size,
        )


@pytest.mark.parametrize(
    "size",
    [
        inf,
        -inf,
        nan,
    ],
)
def test_should_reject_non_finite_size(
    size: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Font size must be finite.",
    ):
        create_font(
            size=size,
        )


@pytest.mark.parametrize(
    "size",
    [
        True,
        False,
        "12",
        None,
        [],
        {},
    ],
)
def test_should_reject_non_numeric_size(
    size: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="Font size must be a numeric value.",
    ):
        Font(
            name="Arial",
            size=size,  # type: ignore[arg-type]
            color=create_color(),
        )


def test_should_require_color_instance() -> None:
    with pytest.raises(
        TypeError,
        match="Font color must be a Color.",
    ):
        Font(
            name="Arial",
            size=12.0,
            color="#000000",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "bold",
        "italic",
        "underline",
        "monospaced",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        0,
        1,
        "true",
        None,
        [],
    ],
)
def test_should_require_boolean_style_flags(
    field_name: str,
    invalid_value: object,
) -> None:
    arguments = {
        "name": "Arial",
        "size": 12.0,
        "color": create_color(),
        field_name: invalid_value,
    }

    with pytest.raises(
        TypeError,
        match=f"Font {field_name} must be a boolean.",
    ):
        Font(**arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "embedded",
    [
        True,
        False,
        None,
    ],
)
def test_should_accept_optional_embedding_state(
    embedded: bool | None,
) -> None:
    font = create_font(
        embedded=embedded,
    )

    assert font.embedded is embedded


@pytest.mark.parametrize(
    "embedded",
    [
        0,
        1,
        "true",
        [],
        {},
    ],
)
def test_should_reject_invalid_embedding_state(
    embedded: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="Font embedded must be a boolean or None.",
    ):
        Font(
            name="Arial",
            size=12.0,
            color=create_color(),
            embedded=embedded,  # type: ignore[arg-type]
        )


def test_should_identify_regular_font() -> None:
    font = create_font()

    assert font.is_regular is True
    assert font.has_emphasis is False
    assert font.style_names == ("regular",)


@pytest.mark.parametrize(
    (
        "bold",
        "italic",
        "underline",
    ),
    [
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, False),
        (True, True, True),
    ],
)
def test_should_identify_emphasized_font(
    bold: bool,
    italic: bool,
    underline: bool,
) -> None:
    font = create_font(
        bold=bold,
        italic=italic,
        underline=underline,
    )

    assert font.is_regular is False
    assert font.has_emphasis is True


def test_monospaced_should_not_remove_regular_status() -> None:
    font = create_font(
        monospaced=True,
    )

    assert font.is_regular is True
    assert font.has_emphasis is False
    assert font.style_names == ("monospaced",)


def test_should_return_style_names_in_stable_order() -> None:
    font = create_font(
        bold=True,
        italic=True,
        underline=True,
        monospaced=True,
    )

    assert font.style_names == (
        "bold",
        "italic",
        "underline",
        "monospaced",
    )


@pytest.mark.parametrize(
    (
        "embedded",
        "expected_known",
        "expected_embedded",
    ),
    [
        (True, True, True),
        (False, True, False),
        (None, False, False),
    ],
)
def test_should_expose_embedding_properties(
    embedded: bool | None,
    expected_known: bool,
    expected_embedded: bool,
) -> None:
    font = create_font(
        embedded=embedded,
    )

    assert font.embedding_known is expected_known
    assert font.is_embedded is expected_embedded


def test_should_be_immutable() -> None:
    font = create_font()

    with pytest.raises(FrozenInstanceError):
        font.name = "Helvetica"  # type: ignore[misc]


def test_equal_fonts_should_have_same_hash() -> None:
    first = create_font(
        name="Arial",
        size=12.0,
        embedded=True,
    )
    second = create_font(
        name="Arial",
        size=12.0,
        embedded=True,
    )

    assert first == second
    assert hash(first) == hash(second)


def test_different_fonts_should_not_be_equal() -> None:
    first = create_font(
        name="Arial",
    )
    second = create_font(
        name="Helvetica",
    )

    assert first != second