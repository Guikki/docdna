from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import logging
from io import BytesIO
from math import ceil, floor
from typing import Any

import pymupdf
import zxingcpp
from PIL import Image, ImageOps

from app.domain.models.barcode import Barcode
from app.domain.readers.base_reader import BaseReader
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.document_location import (
    DocumentLocation,
)


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ScanView:
    """Transformação geométrica de uma tentativa de leitura.

    `rectangle` está nas coordenadas da renderização ORIGINAL em 3x.
    `pre_rotation_size` é o tamanho após eventual redimensionamento, mas
    antes da rotação. Assim, os pontos retornados pelo ZXing podem ser
    mapeados de volta à página, mesmo após corte, escala e rotação.
    """

    image: Image.Image
    rectangle: tuple[int, int, int, int]
    pre_rotation_size: tuple[int, int]
    rotation: int
    tag: str

    def map_bounds(
        self,
        bounds: tuple[float, float, float, float] | None,
    ) -> tuple[float, float, float, float] | None:
        if bounds is None:
            return None

        left, top, right, bottom = bounds
        x0, y0, x1, y1 = self.rectangle
        original_width = x1 - x0
        original_height = y1 - y0
        width, height = self.pre_rotation_size
        if min(original_width, original_height, width, height) <= 0:
            return None

        corners = (
            (left, top), (right, top),
            (right, bottom), (left, bottom),
        )
        mapped = []
        for x, y in corners:
            if self.rotation == 90:  # PIL: anti-horário
                local_x, local_y = width - y, x
            elif self.rotation == 270:  # PIL: horário
                local_x, local_y = y, height - x
            elif self.rotation == 180:
                local_x, local_y = width - x, height - y
            else:
                local_x, local_y = x, y
            mapped.append((
                x0 + local_x * original_width / width,
                y0 + local_y * original_height / height,
            ))

        x_values = [point[0] for point in mapped]
        y_values = [point[1] for point in mapped]
        return min(x_values), min(y_values), max(x_values), max(y_values)


@dataclass
class _Observation:
    result: Any
    bounds: tuple[float, float, float, float] | None
    passes: set[str] = field(default_factory=set)
    baseline: bool = False


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

    # Uma única leitura em 3x permanece o caminho rápido. As passagens
    # adicionais só são feitas quando não há ITF com 44 dígitos iniciado
    # em 8. Esse critério de parada NÃO valida o conteúdo financeiro.
    FALLBACK_RESIZE_RATIO = 0.70

    def read(self, source: str) -> list[Barcode]:
        detected: list[Barcode] = []

        with pymupdf.open(source) as document:
            for page_number, page in enumerate(document, start=1):
                original = self._render_page(page)
                observations: list[_Observation] = []
                try:
                    full_rectangle = (0, 0, original.width, original.height)
                    baseline = _ScanView(
                        image=original,
                        rectangle=full_rectangle,
                        pre_rotation_size=original.size,
                        rotation=0,
                        tag="original",
                    )
                    # A tentativa original conserva o contrato anterior:
                    # se o decodificador falhar aqui, o erro não é ocultado.
                    self._read_view(baseline, observations, baseline=True)

                    if not self._has_complete_payment_itf(observations):
                        for view in self._fallback_views(original):
                            try:
                                # Uma imagem derivada pode ser incompatível
                                # com a versão instalada do decodificador.
                                # Não se descarta a leitura original.
                                self._read_view(view, observations, baseline=False)
                            except (ValueError, TypeError, RuntimeError, OSError):
                                _LOGGER.warning(
                                    "Tentativa de barcode não concluída: "
                                    "página=%d, método=%s",
                                    page_number, view.tag, exc_info=True,
                                )
                            finally:
                                view.image.close()
                    for observation in observations:
                        # Leituras ITF CURTAS novas e leituras novas SEM
                        # coordenadas requerem duas passagens distintas.
                        # Leituras originais são preservadas integralmente.
                        if (
                            not observation.baseline
                            and (
                                self._is_short_itf(observation.result)
                                or observation.bounds is None
                            )
                            and len(observation.passes) < 2
                        ):
                            continue
                        detected.append(self._build_barcode(
                            result=observation.result,
                            page_number=page_number,
                            page_image=original,
                            barcode_index=len(detected) + 1,
                            bounds_override=observation.bounds,
                        ))
                finally:
                    original.close()

        return detected

    def _read_view(
        self,
        view: _ScanView,
        observations: list[_Observation],
        *, baseline: bool,
    ) -> None:
        for result in zxingcpp.read_barcodes(view.image):
            content = str(getattr(result, "text", "") or "").strip()
            if not content:
                continue
            original_bounds = view.map_bounds(self._position_bounds(result))
            matching = next((
                item for item in observations
                if self._same_physical_code(item, result, original_bounds)
            ), None)
            if matching is not None:
                matching.passes.add(view.tag)
                matching.baseline = matching.baseline or baseline
                # Prefere a posição da leitura original caso exista.
                if matching.bounds is None and original_bounds is not None:
                    matching.bounds = original_bounds
                continue
            observations.append(_Observation(
                result=result,
                bounds=original_bounds,
                passes={view.tag},
                baseline=baseline,
            ))

    @staticmethod
    def _format_name(result: Any) -> str:
        return str(getattr(result, "format", "") or "").upper().strip()

    @classmethod
    def _is_itf(cls, result: Any) -> bool:
        normalized = cls._format_name(result).replace("_", "").replace("-", "")
        return normalized == "ITF" or normalized.endswith(".ITF")

    @classmethod
    def _is_short_itf(cls, result: Any) -> bool:
        content = str(getattr(result, "text", "") or "").strip()
        return cls._is_itf(result) and len(content) < 44

    @classmethod
    def _has_complete_payment_itf(cls, observations: list[_Observation]) -> bool:
        return any(
            cls._is_itf(item.result)
            and (text := str(getattr(item.result, "text", "") or "").strip()).isascii()
            and text.isdigit()
            and len(text) == 44
            and text.startswith("8")
            for item in observations
        )

    @classmethod
    def _same_physical_code(
        cls, existing: _Observation, result: Any,
        bounds: tuple[float, float, float, float] | None,
    ) -> bool:
        if cls._format_name(existing.result) != cls._format_name(result):
            return False
        if str(getattr(existing.result, "text", "") or "").strip() != str(
            getattr(result, "text", "") or ""
        ).strip():
            return False
        if existing.bounds is None or bounds is None:
            return existing.bounds is None and bounds is None
        ax0, ay0, ax1, ay1 = existing.bounds
        bx0, by0, bx1, by1 = bounds
        intersection = (
            max(0.0, min(ax1, bx1) - max(ax0, bx0))
            * max(0.0, min(ay1, by1) - max(ay0, by0))
        )
        area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
        area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
        return bool(min(area_a, area_b) > 0 and intersection / min(area_a, area_b) >= 0.45)

    def _fallback_views(self, original: Image.Image):
        """Passagens LIMITADAS, sem dependência nova ou regras por fornecedor.

        Todas as variantes derivam da renderização original: não há nova
        abertura do PDF, e o hash de região é calculado na mesma imagem.
        """
        width, height = original.size
        full = (0, 0, width, height)

        gray = original.convert("L")
        try:
            enhanced = ImageOps.autocontrast(gray, cutoff=1)
        finally:
            gray.close()
        yield _ScanView(enhanced, full, enhanced.size, 0, "contraste")

        resized = original.resize((
            max(1, round(width * self.FALLBACK_RESIZE_RATIO)),
            max(1, round(height * self.FALLBACK_RESIZE_RATIO)),
        ), Image.Resampling.LANCZOS)
        yield _ScanView(resized, full, resized.size, 0, "reduzida")

        rects = (
            ("superior", (0, 0, width, round(height * 0.60))),
            ("inferior", (0, round(height * 0.40), width, height)),
            ("esquerda", (0, 0, round(width * 0.60), height)),
            ("direita", (round(width * 0.40), 0, width, height)),
        )
        for label, rect in rects:
            crop = original.crop(rect)
            yield _ScanView(crop, rect, crop.size, 0, label)

        # Barras verticais próximas das margens, vistas deitadas.
        for label, rect, rotation in (
            ("lateral_esquerda_90", (0, 0, round(width * 0.45), height), 90),
            ("lateral_direita_270", (round(width * 0.55), 0, width, height), 270),
        ):
            crop = original.crop(rect)
            before = crop.size
            try:
                rotated = crop.transpose(
                    Image.Transpose.ROTATE_90 if rotation == 90
                    else Image.Transpose.ROTATE_270
                )
            finally:
                crop.close()
            yield _ScanView(rotated, rect, before, rotation, label)

    def _build_barcode(
        self,
        *,
        result: Any,
        page_number: int,
        page_image: Image.Image,
        barcode_index: int,
        bounds_override: tuple[float, float, float, float] | None = None,
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
                    bounds_override=bounds_override,
                )
            ),
            image_hash=(
                self._build_region_hash(
                    result=result,
                    page_image=page_image,
                    bounds_override=bounds_override,
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
        bounds_override: tuple[float, float, float, float] | None = None,
    ) -> DocumentLocation | None:
        bounds = bounds_override if bounds_override is not None else self._position_bounds(result)

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
        bounds_override: tuple[float, float, float, float] | None = None,
    ) -> str | None:
        bounds = bounds_override if bounds_override is not None else self._position_bounds(result)

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
