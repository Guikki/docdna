from __future__ import annotations

from types import SimpleNamespace

from PIL import Image

from app.domain.readers.barcode_reader import (
    BarcodeReader,
)


def _point(
    x: int,
    y: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        x=x,
        y=y,
    )


def _result(
    *,
    left: int = 30,
    top: int = 60,
    right: int = 330,
    bottom: int = 360,
    text: str = "https://docdna.local",
    barcode_format: str = "QRCode",
    orientation: int = 90,
    ec_level: str = "M",
) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        format=barcode_format,
        orientation=orientation,
        ec_level=ec_level,
        content_type="Text",
        position=SimpleNamespace(
            top_left=_point(
                left,
                top,
            ),
            top_right=_point(
                right,
                top,
            ),
            bottom_right=_point(
                right,
                bottom,
            ),
            bottom_left=_point(
                left,
                bottom,
            ),
        ),
    )


def test_should_convert_render_coordinates_to_pdf_coordinates(
) -> None:
    reader = BarcodeReader()

    location = reader._build_location(
        result=_result(),
        page_number=2,
    )

    assert location is not None
    assert location.page_number == 2

    assert (
        location.bounding_box.x
        == 10.0
    )
    assert (
        location.bounding_box.y
        == 20.0
    )
    assert (
        location.bounding_box.width
        == 100.0
    )
    assert (
        location.bounding_box.height
        == 100.0
    )


def test_should_build_deterministic_hash_for_detected_region(
) -> None:
    reader = BarcodeReader()

    image = Image.new(
        "RGB",
        (500, 500),
        "white",
    )

    try:
        first_hash = (
            reader
            ._build_region_hash(
                result=_result(),
                page_image=image,
            )
        )

        second_hash = (
            reader
            ._build_region_hash(
                result=_result(),
                page_image=image,
            )
        )
    finally:
        image.close()

    assert first_hash is not None
    assert len(first_hash) == 64
    assert first_hash == second_hash


def test_should_preserve_zxing_metadata_in_barcode(
) -> None:
    reader = BarcodeReader()

    image = Image.new(
        "RGB",
        (500, 500),
        "white",
    )

    try:
        barcode = reader._build_barcode(
            result=_result(),
            page_number=3,
            page_image=image,
            barcode_index=4,
        )
    finally:
        image.close()

    assert barcode.barcode_index == 4
    assert barcode.page_number == 3
    assert barcode.format == "QRCode"
    assert (
        barcode.content
        == "https://docdna.local"
    )

    assert barcode.location is not None
    assert barcode.orientation == 90.0
    assert barcode.error_correction == "M"
    assert barcode.content_type == "Text"
    assert barcode.image_hash is not None


def test_should_return_none_when_position_is_unavailable(
) -> None:
    reader = BarcodeReader()

    result = SimpleNamespace(
        text="value",
        format="QRCode",
        position=None,
    )

    assert (
        reader._build_location(
            result=result,
            page_number=1,
        )
        is None
    )


def test_should_return_none_hash_when_position_is_unavailable(
) -> None:
    reader = BarcodeReader()

    image = Image.new(
        "RGB",
        (100, 100),
        "white",
    )

    try:
        result = SimpleNamespace(
            position=None,
        )

        assert (
            reader
            ._build_region_hash(
                result=result,
                page_image=image,
            )
            is None
        )
    finally:
        image.close()
