import math

import pytest

from app.domain.document.models.bounding_box import BoundingBox


def test_should_create_bounding_box() -> None:
    bounding_box = BoundingBox(
        left=10,
        top=20,
        right=110,
        bottom=70,
    )

    assert bounding_box.left == 10.0
    assert bounding_box.top == 20.0
    assert bounding_box.right == 110.0
    assert bounding_box.bottom == 70.0

    assert bounding_box.width == 100.0
    assert bounding_box.height == 50.0
    assert bounding_box.area == 5000.0
    assert bounding_box.center == (60.0, 45.0)
    assert bounding_box.has_area is True


def test_should_create_bounding_box_from_position_and_size() -> None:
    bounding_box = BoundingBox.from_position_and_size(
        left=10,
        top=20,
        width=100,
        height=50,
    )

    assert bounding_box == BoundingBox(
        left=10,
        top=20,
        right=110,
        bottom=70,
    )


def test_should_allow_zero_area_bounding_box() -> None:
    bounding_box = BoundingBox(
        left=10,
        top=20,
        right=10,
        bottom=20,
    )

    assert bounding_box.width == 0.0
    assert bounding_box.height == 0.0
    assert bounding_box.area == 0.0
    assert bounding_box.has_area is False


@pytest.mark.parametrize(
    ("left", "top", "right", "bottom"),
    [
        (10, 0, 9, 10),
        (0, 10, 10, 9),
    ],
)
def test_should_reject_inverted_coordinates(
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> None:
    with pytest.raises(ValueError):
        BoundingBox(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
        )


@pytest.mark.parametrize(
    "value",
    [
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_should_reject_non_finite_coordinates(
    value: float,
) -> None:
    with pytest.raises(ValueError, match="finite"):
        BoundingBox(
            left=value,
            top=0,
            right=10,
            bottom=10,
        )


def test_should_reject_boolean_coordinate() -> None:
    with pytest.raises(TypeError, match="numeric"):
        BoundingBox(
            left=True,
            top=0,
            right=10,
            bottom=10,
        )


@pytest.mark.parametrize(
    ("width", "height"),
    [
        (-1, 10),
        (10, -1),
    ],
)
def test_should_reject_negative_dimensions(
    width: float,
    height: float,
) -> None:
    with pytest.raises(ValueError):
        BoundingBox.from_position_and_size(
            left=0,
            top=0,
            width=width,
            height=height,
        )


def test_should_detect_contained_point() -> None:
    bounding_box = BoundingBox(
        left=10,
        top=20,
        right=110,
        bottom=70,
    )

    assert bounding_box.contains_point(x=60, y=45) is True
    assert bounding_box.contains_point(x=10, y=20) is True
    assert bounding_box.contains_point(x=110, y=70) is True

    assert bounding_box.contains_point(
        x=10,
        y=20,
        inclusive=False,
    ) is False

    assert bounding_box.contains_point(x=200, y=45) is False


def test_should_detect_contained_box() -> None:
    outer = BoundingBox(
        left=0,
        top=0,
        right=100,
        bottom=100,
    )

    inner = BoundingBox(
        left=20,
        top=20,
        right=80,
        bottom=80,
    )

    assert outer.contains_box(inner) is True
    assert inner.contains_box(outer) is False


def test_should_detect_positive_area_intersection() -> None:
    first = BoundingBox(
        left=0,
        top=0,
        right=100,
        bottom=100,
    )

    second = BoundingBox(
        left=50,
        top=50,
        right=150,
        bottom=150,
    )

    assert first.intersects(second) is True

    assert first.intersection(second) == BoundingBox(
        left=50,
        top=50,
        right=100,
        bottom=100,
    )

    assert first.intersection_area(second) == 2500.0
    assert first.intersection_ratio(second) == pytest.approx(0.25)
    assert first.iou(second) == pytest.approx(
        2500 / 17500
    )


def test_touching_edges_should_not_have_positive_area_intersection() -> None:
    first = BoundingBox(
        left=0,
        top=0,
        right=100,
        bottom=100,
    )

    second = BoundingBox(
        left=100,
        top=0,
        right=200,
        bottom=100,
    )

    assert first.intersects(second) is False

    assert first.intersects(
        second,
        include_edges=True,
    ) is True

    assert first.intersection(second) is None
    assert first.intersection_area(second) == 0.0
    assert first.iou(second) == 0.0


def test_should_return_zero_intersection_ratio_for_zero_area_box() -> None:
    zero_area = BoundingBox(
        left=10,
        top=10,
        right=10,
        bottom=20,
    )

    other = BoundingBox(
        left=0,
        top=0,
        right=100,
        bottom=100,
    )

    assert zero_area.intersection_ratio(other) == 0.0


def test_should_translate_bounding_box() -> None:
    bounding_box = BoundingBox(
        left=10,
        top=20,
        right=110,
        bottom=70,
    )

    translated = bounding_box.translated(
        delta_x=5,
        delta_y=-10,
    )

    assert translated == BoundingBox(
        left=15,
        top=10,
        right=115,
        bottom=60,
    )

    assert bounding_box == BoundingBox(
        left=10,
        top=20,
        right=110,
        bottom=70,
    )


def test_should_reject_invalid_other_box() -> None:
    bounding_box = BoundingBox(
        left=0,
        top=0,
        right=100,
        bottom=100,
    )

    with pytest.raises(TypeError, match="another BoundingBox"):
        bounding_box.intersects("invalid")