from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from math import ceil, floor
from typing import Any

import pymupdf
import zxingcpp
from PIL import Image

from app.domain.models.barcode import Barcode
from app.domain.readers.base_reader import BaseReader
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.document_location import (
    DocumentLocation,
)


class BarcodeReader(BaseReader):
    """
    Lê códigos de barras e QR Codes a partir da página renderizada.

    Além de conteúdo e formato, preserva quando disponível:
    - posição real informada pelo ZXing;
    - orientação;
    - nível de correção de erro;
    - tipo de conteúdo;
    - SHA-256 dos pixels da região visual detectada.

    Nenhum desses dados representa, isoladamente, evidência de fraude.
    """

    RENDER_SCALE = 3.0

    def read(
        self,
        source: str,
    ) -> list[Barcode]:
        detected_barcodes: list[Barcode] = []

        with pymupdf.open(source) as document:
            for page_number, page in enumerate(
                document,
                start=1,
            ):
                page_image = self._render_page(
                    page
                )

                results = zxingcpp.read_barcodes(
                    page_image
                )

                for result in results:
                    content = (
                        str(
                            getattr(
                                result,
                                "text",
                                "",
                            )
                            or ""
                        )
                        .strip()
                    )

                    if not content:
                        continue

                    detected_barcodes.append(
                        self._build_barcode(
                            result=result,
                            page_number=page_number,
                            page_image=page_image,
                            barcode_index=(
                                len(
                                    detected_barcodes
                                )
                                + 1
                            ),
                        )
                    )

        return detected_barcodes

    def _build_barcode(
        self,
        *,
        result: Any,
        page_number: int,
        page_image: Image.Image,
        barcode_index: int,
    ) -> Barcode:
        return Barcode(
            barcode_index=barcode_index,
            page_number=page_number,
            format=str(
                getattr(
                    result,
                    "format",
                    "",
                )
                or ""
            ),
            content=(
                str(
                    getattr(
                        result,
                        "text",
                        "",
                    )
                    or ""
                )
                .strip()
            ),
            location=(
                self._build_location(
                    result=result,
                    page_number=page_number,
                )
            ),
            image_hash=(
                self._build_region_hash(
                    result=result,
                    page_image=page_image,
                )
            ),
            orientation=(
                self._orientation_value(
                    getattr(
                        result,
                        "orientation",
                        0.0,
                    )
                )
            ),
            error_correction=(
                self._optional_text(
                    getattr(
                        result,
                        "ec_level",
                        None,
                    )
                )
            ),
            content_type=(
                self._optional_text(
                    getattr(
                        result,
                        "content_type",
                        None,
                    )
                )
            ),
        )

    def _build_location(
        self,
        *,
        result: Any,
        page_number: int,
    ) -> DocumentLocation | None:
        bounds = self._position_bounds(
            result
        )

        if bounds is None:
            return None

        left, top, right, bottom = bounds

        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            return None

        return DocumentLocation(
            page_number=page_number,
            bounding_box=BoundingBox(
                x=(
                    left
                    / self.RENDER_SCALE
                ),
                y=(
                    top
                    / self.RENDER_SCALE
                ),
                width=(
                    width
                    / self.RENDER_SCALE
                ),
                height=(
                    height
                    / self.RENDER_SCALE
                ),
            ),
        )

    def _build_region_hash(
        self,
        *,
        result: Any,
        page_image: Image.Image,
    ) -> str | None:
        bounds = self._position_bounds(
            result
        )

        if bounds is None:
            return None

        left, top, right, bottom = bounds

        crop_left = max(
            0,
            floor(left),
        )
        crop_top = max(
            0,
            floor(top),
        )
        crop_right = min(
            page_image.width,
            ceil(right),
        )
        crop_bottom = min(
            page_image.height,
            ceil(bottom),
        )

        if (
            crop_right <= crop_left
            or crop_bottom <= crop_top
        ):
            return None

        region = (
            page_image
            .crop(
                (
                    crop_left,
                    crop_top,
                    crop_right,
                    crop_bottom,
                )
            )
            .convert(
                "RGB"
            )
        )

        try:
            payload = (
                region.width.to_bytes(
                    4,
                    byteorder="big",
                    signed=False,
                )
                + region.height.to_bytes(
                    4,
                    byteorder="big",
                    signed=False,
                )
                + region.tobytes()
            )

            return sha256(
                payload
            ).hexdigest()
        finally:
            region.close()

    def _position_bounds(
        self,
        result: Any,
    ) -> tuple[
        float,
        float,
        float,
        float,
    ] | None:
        position = getattr(
            result,
            "position",
            None,
        )

        if position is None:
            return None

        points = []

        for attribute_name in (
            "top_left",
            "top_right",
            "bottom_right",
            "bottom_left",
        ):
            point = getattr(
                position,
                attribute_name,
                None,
            )

            if point is None:
                return None

            x = getattr(
                point,
                "x",
                None,
            )
            y = getattr(
                point,
                "y",
                None,
            )

            if x is None or y is None:
                return None

            try:
                points.append(
                    (
                        float(x),
                        float(y),
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                return None

        x_values = [
            point[0]
            for point
            in points
        ]
        y_values = [
            point[1]
            for point
            in points
        ]

        return (
            min(x_values),
            min(y_values),
            max(x_values),
            max(y_values),
        )

    def _render_page(
        self,
        page: pymupdf.Page,
    ) -> Image.Image:
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(
                self.RENDER_SCALE,
                self.RENDER_SCALE,
            ),
            alpha=False,
        )

        image_bytes = pixmap.tobytes(
            "png"
        )

        return (
            Image.open(
                BytesIO(
                    image_bytes
                )
            )
            .convert(
                "RGB"
            )
        )

    @staticmethod
    def _optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return (
            normalized
            if normalized
            else None
        )

    @staticmethod
    def _orientation_value(
        value: Any,
    ) -> float:
        try:
            return float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0.0
