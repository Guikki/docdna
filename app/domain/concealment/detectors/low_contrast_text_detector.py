from __future__ import annotations

from math import isfinite

from app.domain.concealment.models.text_concealment_finding import (
    TextConcealmentFinding,
)
from app.domain.concealment.services.local_background_color_sampler import (
    LocalBackgroundColorSampler,
)
from app.domain.document.models.document import Document
from app.domain.document.models.text_span import TextSpan


class LowContrastTextDetector:
    """
    Detecta texto nativo com contraste muito baixo em relação ao fundo local.

    A razão de contraste é calculada pela implementação WCAG já presente no
    value object Color do domínio documental. O detector usa uma régua
    forense própria: razão inferior a 2.00:1 constitui indicador técnico de
    possível ocultação; abaixo de 1.50:1 o indicador é classificado como forte.

    O detector não conclui fraude ou intenção maliciosa.
    """

    CODE = "low_contrast_text"
    NAME = "low_contrast_text_detector"

    DEFAULT_LOW_CONTRAST_THRESHOLD = 2.0
    DEFAULT_EXTREME_LOW_CONTRAST_THRESHOLD = 1.5

    OCR_TECHNICAL_FONT_NAME = "OCR_UNKNOWN"
    NEAR_WHITE_CHANNEL_MIN = 245

    def __init__(
        self,
        *,
        background_sampler: LocalBackgroundColorSampler | None = None,
        low_contrast_threshold: float = (
            DEFAULT_LOW_CONTRAST_THRESHOLD
        ),
        extreme_low_contrast_threshold: float = (
            DEFAULT_EXTREME_LOW_CONTRAST_THRESHOLD
        ),
    ) -> None:
        self._background_sampler = (
            background_sampler
            or LocalBackgroundColorSampler()
        )
        self._low_contrast_threshold = (
            self._validate_threshold(
                low_contrast_threshold,
                name="low_contrast_threshold",
            )
        )
        self._extreme_low_contrast_threshold = (
            self._validate_threshold(
                extreme_low_contrast_threshold,
                name=(
                    "extreme_low_contrast_threshold"
                ),
            )
        )

        if (
            self._extreme_low_contrast_threshold
            >= self._low_contrast_threshold
        ):
            raise ValueError(
                "LowContrastTextDetector extreme threshold must be "
                "lower than low contrast threshold."
            )

    @property
    def low_contrast_threshold(self) -> float:
        return self._low_contrast_threshold

    @property
    def extreme_low_contrast_threshold(self) -> float:
        return self._extreme_low_contrast_threshold

    def detect(
        self,
        document: Document,
        *,
        pdf_path: str,
    ) -> list[TextConcealmentFinding]:
        if not isinstance(document, Document):
            raise TypeError(
                "LowContrastTextDetector document must be a Document."
            )

        if not isinstance(pdf_path, str):
            raise TypeError(
                "LowContrastTextDetector pdf_path must be a string."
            )

        if not pdf_path.strip():
            raise ValueError(
                "LowContrastTextDetector pdf_path must not be empty."
            )

        findings: list[TextConcealmentFinding] = []

        self._clear_background_cache()
        try:
            for page in document.pages:
                for span in page.text_spans:
                    finding = self._analyze_span(
                        span=span,
                        pdf_path=pdf_path,
                    )

                    if finding is not None:
                        findings.append(finding)
        finally:
            self._clear_background_cache()

        return findings

    def _analyze_span(
        self,
        *,
        span: TextSpan,
        pdf_path: str,
    ) -> TextConcealmentFinding | None:
        if not span.text.strip():
            return None

        if (
            span.font.name
            == self.OCR_TECHNICAL_FONT_NAME
        ):
            return None

        background = (
            self._background_sampler.sample(
                pdf_path=pdf_path,
                span=span,
            )
        )

        if background is None:
            return None

        text_color = span.font.color
        background_color = background.color

        contrast_ratio = (
            text_color.contrast_ratio(
                background_color
            )
        )

        if (
            contrast_ratio
            >= self._low_contrast_threshold
        ):
            return None

        is_extreme = (
            contrast_ratio
            < self._extreme_low_contrast_threshold
        )

        signals = [
            "low_contrast",
            "background_color_estimated",
        ]

        if is_extreme:
            signals.append(
                "extreme_low_contrast"
            )

        if background.dominance_ratio >= 0.75:
            signals.append(
                "high_background_dominance"
            )

        is_near_white = all(
            channel
            >= self.NEAR_WHITE_CHANNEL_MIN
            for channel in text_color.rgb255
        )

        return TextConcealmentFinding(
            code=self.CODE,
            detector=self.NAME,
            page_number=span.page_number,
            text=span.text,
            bounding_box=span.bounding_box,
            font_name=span.font.name,
            font_size=span.font.size,
            font_color_hex=text_color.to_hex(),
            confidence=self._calculate_confidence(
                contrast_ratio=contrast_ratio,
                background_dominance_ratio=(
                    background.dominance_ratio
                ),
            ),
            signals=tuple(signals),
            is_near_white=is_near_white,
            is_small_text=False,
            is_relative_small_text=False,
            is_instruction_like=False,
            background_color_hex=(
                background_color.to_hex()
            ),
            font_relative_luminance=round(
                text_color.relative_luminance,
                6,
            ),
            background_relative_luminance=round(
                background_color.relative_luminance,
                6,
            ),
            contrast_ratio=round(
                contrast_ratio,
                6,
            ),
            contrast_threshold=(
                self._low_contrast_threshold
            ),
            contrast_level=(
                "extreme_low_contrast"
                if is_extreme
                else "low_contrast"
            ),
            background_sampling_method=(
                background.method
            ),
            background_dominance_ratio=round(
                background.dominance_ratio,
                6,
            ),
            is_low_contrast=True,
            is_extreme_low_contrast=is_extreme,
        )

    def _calculate_confidence(
        self,
        *,
        contrast_ratio: float,
        background_dominance_ratio: float,
    ) -> float:
        contrast_strength = (
            self._low_contrast_threshold
            - contrast_ratio
        ) / (
            self._low_contrast_threshold
            - 1.0
        )

        contrast_strength = max(
            0.0,
            min(contrast_strength, 1.0),
        )

        confidence = (
            0.60
            + 0.25 * contrast_strength
            + 0.15 * background_dominance_ratio
        )

        return min(
            round(confidence, 4),
            1.0,
        )

    def _clear_background_cache(self) -> None:
        clear_cache = getattr(
            self._background_sampler,
            "clear_cache",
            None,
        )
        if callable(clear_cache):
            clear_cache()

    @staticmethod
    def _validate_threshold(
        value: float,
        *,
        name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float),
            )
        ):
            raise TypeError(
                f"LowContrastTextDetector {name} must be numeric."
            )

        normalized = float(value)
        if not isfinite(normalized):
            raise ValueError(
                f"LowContrastTextDetector {name} must be finite."
            )

        if not 1.0 < normalized <= 21.0:
            raise ValueError(
                f"LowContrastTextDetector {name} must be "
                "greater than 1.0 and at most 21.0."
            )

        return normalized
