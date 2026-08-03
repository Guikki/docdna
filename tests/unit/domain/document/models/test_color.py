import math

import pytest

from app.domain.document.models.color import Color


def test_should_create_normalized_color() -> None:
    color = Color(
        red=1,
        green=0.5,
        blue=0,
        alpha=0.75,
    )

    assert color.red == 1.0
    assert color.green == 0.5
    assert color.blue == 0.0
    assert color.alpha == 0.75
    assert color.rgb == (1.0, 0.5, 0.0)
    assert color.rgba == (1.0, 0.5, 0.0, 0.75)


def test_should_create_color_from_rgb255() -> None:
    color = Color.from_rgb255(
        red=255,
        green=128,
        blue=0,
        alpha=64,
    )

    assert color.red == 1.0
    assert color.green == pytest.approx(128 / 255)
    assert color.blue == 0.0
    assert color.alpha == pytest.approx(64 / 255)

    assert color.rgba255 == (
        255,
        128,
        0,
        64,
    )


@pytest.mark.parametrize(
    ("hex_value", "expected_rgba"),
    [
        ("#FFFFFF", (255, 255, 255, 255)),
        ("000000", (0, 0, 0, 255)),
        ("#FF000080", (255, 0, 0, 128)),
        ("00FF00FF", (0, 255, 0, 255)),
    ],
)
def test_should_create_color_from_hex(
    hex_value: str,
    expected_rgba: tuple[int, int, int, int],
) -> None:
    color = Color.from_hex(hex_value)

    assert color.rgba255 == expected_rgba


@pytest.mark.parametrize(
    "hex_value",
    [
        "",
        "#FFF",
        "#FFFFF",
        "#FFFFFFFFF",
        "#GG0000",
    ],
)
def test_should_reject_invalid_hex_color(
    hex_value: str,
) -> None:
    with pytest.raises(ValueError):
        Color.from_hex(hex_value)


@pytest.mark.parametrize(
    "channel_value",
    [
        -0.01,
        1.01,
    ],
)
def test_should_reject_normalized_channel_outside_range(
    channel_value: float,
) -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        Color(
            red=channel_value,
            green=0.0,
            blue=0.0,
        )


@pytest.mark.parametrize(
    "channel_value",
    [
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_should_reject_non_finite_channel(
    channel_value: float,
) -> None:
    with pytest.raises(ValueError, match="finite"):
        Color(
            red=channel_value,
            green=0.0,
            blue=0.0,
        )


def test_should_reject_boolean_channel() -> None:
    with pytest.raises(TypeError, match="numeric"):
        Color(
            red=True,
            green=0.0,
            blue=0.0,
        )


@pytest.mark.parametrize(
    "channel_value",
    [
        -1,
        256,
    ],
)
def test_should_reject_rgb255_channel_outside_range(
    channel_value: int,
) -> None:
    with pytest.raises(ValueError, match="between 0 and 255"):
        Color.from_rgb255(
            red=channel_value,
            green=0,
            blue=0,
        )


def test_should_identify_transparency_state() -> None:
    transparent = Color(
        red=0.0,
        green=0.0,
        blue=0.0,
        alpha=0.0,
    )

    opaque = Color(
        red=0.0,
        green=0.0,
        blue=0.0,
        alpha=1.0,
    )

    assert transparent.is_fully_transparent is True
    assert transparent.is_fully_opaque is False

    assert opaque.is_fully_transparent is False
    assert opaque.is_fully_opaque is True


def test_black_and_white_should_have_maximum_contrast() -> None:
    black = Color.from_hex("#000000")
    white = Color.from_hex("#FFFFFF")

    assert black.relative_luminance == pytest.approx(0.0)
    assert white.relative_luminance == pytest.approx(1.0)

    assert black.contrast_ratio(white) == pytest.approx(21.0)
    assert white.contrast_ratio(black) == pytest.approx(21.0)


def test_equal_colors_should_have_minimum_contrast() -> None:
    color = Color.from_hex("#336699")

    assert color.contrast_ratio(color) == pytest.approx(1.0)


def test_should_calculate_normalized_color_distance() -> None:
    black = Color.from_hex("#000000")
    white = Color.from_hex("#FFFFFF")

    assert black.distance(black) == pytest.approx(0.0)
    assert black.distance(white) == pytest.approx(1.0)


def test_should_identify_close_colors() -> None:
    first = Color.from_rgb255(
        red=250,
        green=250,
        blue=250,
    )

    second = Color.from_rgb255(
        red=255,
        green=255,
        blue=255,
    )

    assert first.is_close_to(
        second,
        threshold=0.02,
    ) is True

    assert first.is_close_to(
        second,
        threshold=0.005,
    ) is False


@pytest.mark.parametrize(
    "threshold",
    [
        -0.01,
        1.01,
        math.inf,
        math.nan,
    ],
)
def test_should_reject_invalid_distance_threshold(
    threshold: float,
) -> None:
    first = Color.from_hex("#000000")
    second = Color.from_hex("#FFFFFF")

    with pytest.raises(ValueError):
        first.is_close_to(
            second,
            threshold=threshold,
        )


def test_should_composite_semitransparent_color_over_background() -> None:
    foreground = Color(
        red=1.0,
        green=0.0,
        blue=0.0,
        alpha=0.5,
    )

    background = Color(
        red=1.0,
        green=1.0,
        blue=1.0,
        alpha=1.0,
    )

    result = foreground.composite_over(background)

    assert result.red == pytest.approx(1.0)
    assert result.green == pytest.approx(0.5)
    assert result.blue == pytest.approx(0.5)
    assert result.alpha == pytest.approx(1.0)


def test_should_composite_two_fully_transparent_colors() -> None:
    transparent = Color(
        red=0.5,
        green=0.5,
        blue=0.5,
        alpha=0.0,
    )

    result = transparent.composite_over(transparent)

    assert result == Color(
        red=0.0,
        green=0.0,
        blue=0.0,
        alpha=0.0,
    )


@pytest.mark.parametrize(
    ("include_alpha", "expected"),
    [
        (False, "#FF8000"),
        (True, "#FF800080"),
    ],
)
def test_should_convert_color_to_hex(
    include_alpha: bool,
    expected: str,
) -> None:
    color = Color.from_rgb255(
        red=255,
        green=128,
        blue=0,
        alpha=128,
    )

    assert color.to_hex(
        include_alpha=include_alpha,
    ) == expected


def test_should_reject_invalid_other_color() -> None:
    color = Color.from_hex("#000000")

    with pytest.raises(TypeError, match="another Color"):
        color.distance("invalid")