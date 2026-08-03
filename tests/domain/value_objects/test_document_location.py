import pytest

from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.document_location import (
    DocumentLocation,
)


def test_location():
    location = DocumentLocation(
        page_number=2,
        bounding_box=BoundingBox(0, 0, 100, 50),
    )

    assert location.page_number == 2


def test_invalid_page():
    with pytest.raises(ValueError):
        DocumentLocation(
            page_number=0,
            bounding_box=BoundingBox(0, 0, 10, 10),
        )