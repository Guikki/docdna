from __future__ import annotations

from collections import Counter
from math import ceil, floor, isfinite
from pathlib import Path
from statistics import median

import pymupdf
from PIL import Image

from app.domain.concealment.models.background_color_estimate import (
    BackgroundColorEstimate,
)
from app.domain.document.models.color import Color
from app.domain.document.models.text_span import TextSpan


class LocalBackgroundColorSampler:
    """
    Estima a cor de fundo local de um TextSpan a partir da página renderizada.

    A região analisada é a própria bounding box nativa do texto. As cores são
    agrupadas em buckets para reduzir ruído de antialiasing. O resultado só é
    aceito quando um grupo cromático domina a região com confiança mínima.

    Regiões visualmente complexas ou sem cor dominante retornam None. Essa
    escolha é deliberadamente conservadora para evitar falso positivo.
    """

    METHOD = "dominant_quantized_bbox_color"

    DEFAULT_RENDER_SCALE = 2.0
    DEFAULT_BUCKET_SIZE = 16
    DEFAULT_MINIMUM_DOMINANCE_RATIO = 0.55

    def __init__(
        self,
        *,
        render_scale: float = DEFAULT_RENDER_SCALE,
        bucket_size: int = DEFAULT_BUCKET_SIZE,
        minimum_dominance_ratio: float = (
            DEFAULT_MINIMUM_DOMINANCE_RATIO
        ),
    ) -> None:
        self._render_scale = self._validate_render_scale(
            render_scale
        )
        self._bucket_size = self._validate_bucket_size(
            bucket_size
        )
        self._minimum_dominance_ratio = (
            self._validate_dominance_ratio(
                minimum_dominance_ratio
            )
        )
        self._page_cache: dict[
            tuple[str, int],
            Image.Image,
        ] = {}

    @property
    def render_scale(self) -> float:
        return self._render_scale

    @property
    def bucket_size(self) -> int:
        return self._bucket_size

    @property
    def minimum_dominance_ratio(self) -> float:
        return self._minimum_dominance_ratio

    def sample(
        self,
        *,
        pdf_path: str,
        span: TextSpan,
    ) -> BackgroundColorEstimate | None:
        if not isinstance(pdf_path, str):
            raise TypeError(
                "LocalBackgroundColorSampler pdf_path must be a string."
            )

        normalized_path = pdf_path.strip()
        if not normalized_path:
            raise ValueError(
                "LocalBackgroundColorSampler pdf_path must not be empty."
            )

        if not isinstance(span, TextSpan):
            raise TypeError(
                "LocalBackgroundColorSampler span must be a TextSpan."
            )

        source_path = Path(normalized_path)
        if not source_path.exists():
            raise FileNotFoundError(
                f"PDF source not found: {normalized_path}"
            )

        image = self._get_rendered_page(
            pdf_path=normalized_path,
            page_number=span.page_number,
        )

        crop = self._crop_span_region(
            image=image,
            span=span,
        )

        if crop is None:
            return None

        return self._estimate_dominant_color(crop)

    def clear_cache(self) -> None:
        """Release rendered-page images cached for the current analysis."""
        self._page_cache.clear()

    def _get_rendered_page(
        self,
        *,
        pdf_path: str,
        page_number: int,
    ) -> Image.Image:
        cache_key = (
            str(Path(pdf_path).resolve()),
            page_number,
        )

        cached = self._page_cache.get(
            cache_key
        )
        if cached is not None:
            return cached

        image = self._render_page(
            pdf_path=pdf_path,
            page_number=page_number,
        )
        self._page_cache[cache_key] = image
        return image

    def _render_page(
        self,
        *,
        pdf_path: str,
        page_number: int,
    ) -> Image.Image:
        matrix = pymupdf.Matrix(
            self._render_scale,
            self._render_scale,
        )

        with pymupdf.open(pdf_path) as document:
            if page_number < 1:
                raise ValueError(
                    "TextSpan page_number must be greater than or equal to 1."
                )

            if page_number > len(document):
                raise ValueError(
                    "TextSpan page_number exceeds PDF page count."
                )

            page = document.load_page(
                page_number - 1
            )
            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )

            return Image.frombytes(
                "RGB",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            )

    def _crop_span_region(
        self,
        *,
        image: Image.Image,
        span: TextSpan,
    ) -> Image.Image | None:
        box = span.bounding_box

        left = max(
            floor(box.left * self._render_scale),
            0,
        )
        top = max(
            floor(box.top * self._render_scale),
            0,
        )
        right = min(
            ceil(box.right * self._render_scale),
            image.width,
        )
        bottom = min(
            ceil(box.bottom * self._render_scale),
            image.height,
        )

        if right <= left or bottom <= top:
            return None

        return image.crop(
            (left, top, right, bottom)
        ).convert("RGB")

    def _estimate_dominant_color(
        self,
        image: Image.Image,
    ) -> BackgroundColorEstimate | None:
        pixels = list(
            image.get_flattened_data()
        )

        if not pixels:
            return None

        bucket_counts = Counter(
            self._bucket_key(pixel)
            for pixel in pixels
        )

        dominant_bucket, dominant_count = (
            bucket_counts.most_common(1)[0]
        )

        dominance_ratio = (
            dominant_count
            / len(pixels)
        )

        if (
            dominance_ratio
            < self._minimum_dominance_ratio
        ):
            return None

        dominant_pixels = [
            pixel
            for pixel in pixels
            if self._bucket_key(pixel)
            == dominant_bucket
        ]

        red = round(
            median(
                pixel[0]
                for pixel in dominant_pixels
            )
        )
        green = round(
            median(
                pixel[1]
                for pixel in dominant_pixels
            )
        )
        blue = round(
            median(
                pixel[2]
                for pixel in dominant_pixels
            )
        )

        return BackgroundColorEstimate(
            color=Color.from_rgb255(
                red=red,
                green=green,
                blue=blue,
            ),
            dominance_ratio=round(
                dominance_ratio,
                6,
            ),
            sampled_pixel_count=len(pixels),
            method=self.METHOD,
        )

    def _bucket_key(
        self,
        pixel: tuple[int, int, int],
    ) -> tuple[int, int, int]:
        return tuple(
            min(
                255,
                (channel // self._bucket_size)
                * self._bucket_size,
            )
            for channel in pixel
        )  # type: ignore[return-value]

    @staticmethod
    def _validate_render_scale(
        value: float,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float),
            )
        ):
            raise TypeError(
                "LocalBackgroundColorSampler render_scale must be numeric."
            )

        normalized = float(value)
        if not isfinite(normalized):
            raise ValueError(
                "LocalBackgroundColorSampler render_scale must be finite."
            )

        if normalized <= 0.0:
            raise ValueError(
                "LocalBackgroundColorSampler render_scale "
                "must be greater than zero."
            )

        return normalized

    @staticmethod
    def _validate_bucket_size(
        value: int,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise TypeError(
                "LocalBackgroundColorSampler bucket_size must be an integer."
            )

        if not 1 <= value <= 256:
            raise ValueError(
                "LocalBackgroundColorSampler bucket_size "
                "must be between 1 and 256."
            )

        return value

    @staticmethod
    def _validate_dominance_ratio(
        value: float,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float),
            )
        ):
            raise TypeError(
                "LocalBackgroundColorSampler minimum_dominance_ratio "
                "must be numeric."
            )

        normalized = float(value)
        if not isfinite(normalized):
            raise ValueError(
                "LocalBackgroundColorSampler minimum_dominance_ratio "
                "must be finite."
            )

        if not 0.0 < normalized <= 1.0:
            raise ValueError(
                "LocalBackgroundColorSampler minimum_dominance_ratio "
                "must be greater than zero and at most 1.0."
            )

        return normalized
