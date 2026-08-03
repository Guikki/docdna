import pytest

from app.domain.value_objects.bounding_box import BoundingBox


def test_area():
    box = BoundingBox(10, 20, 30, 40)

    assert box.area == 1200


def test_right():
    box = BoundingBox(10, 0, 25, 10)

    assert box.right == 35


def test_bottom():
    box = BoundingBox(0, 15, 10, 20)

    assert box.bottom == 35


def test_intersection():
    a = BoundingBox(0, 0, 100, 100)
    b = BoundingBox(50, 50, 100, 100)

    assert a.intersects(b)


def test_no_intersection():
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(100, 100, 10, 10)

    assert not a.intersects(b)


@pytest.mark.parametrize("width", [0, -1])
def test_invalid_width(width):
    with pytest.raises(ValueError):
        BoundingBox(0, 0, width, 10)


@pytest.mark.parametrize("height", [0, -5])
def test_invalid_height(height):
    with pytest.raises(ValueError):
        BoundingBox(0, 0, 10, height)