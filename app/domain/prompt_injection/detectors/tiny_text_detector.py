from __future__ import annotations

from collections.abc import Iterable

from app.domain.document.models.text_span import TextSpan
from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)


class TinyTextDetector:
    """
    Detecta texto renderizado com tamanho de fonte
    anormalmente pequeno.

    Este detector identifica uma característica de possível
    ocultação tipográfica. Ele não conclui, isoladamente,
    pela existência de Prompt Injection.

    A correlação com conteúdo instrucional suspeito é
    responsabilidade da camada de análise/assessment.
    """

    DETECTOR_NAME = "tiny_text"

    EVIDENCE_CODE = "PROMPT_INJECTION_TINY_TEXT"

    CATEGORY = "visual_concealment"

    DEFAULT_MAXIMUM_FONT_SIZE = 4.0

    def __init__(
        self,
        *,
        maximum_font_size: float = DEFAULT_MAXIMUM_FONT_SIZE,
    ) -> None:
        if (
            isinstance(maximum_font_size, bool)
            or not isinstance(
                maximum_font_size,
                (int, float),
            )
        ):
            raise TypeError(
                "TinyTextDetector maximum_font_size "
                "must be numeric."
            )

        normalized_maximum_font_size = float(
            maximum_font_size
        )

        if normalized_maximum_font_size <= 0.0:
            raise ValueError(
                "TinyTextDetector maximum_font_size "
                "must be greater than zero."
            )

        self._maximum_font_size = (
            normalized_maximum_font_size
        )

    @property
    def name(self) -> str:
        return self.DETECTOR_NAME

    @property
    def maximum_font_size(self) -> float:
        return self._maximum_font_size

    def detect(
        self,
        *,
        spans: Iterable[TextSpan],
    ) -> tuple[
        PromptInjectionEvidence,
        ...
    ]:
        """
        Analisa uma coleção de TextSpan e retorna
        uma evidência para cada span cujo tamanho
        da fonte esteja abaixo do limite configurado.
        """

        if isinstance(
            spans,
            (str, bytes),
        ):
            raise TypeError(
                "TinyTextDetector spans must be "
                "an iterable of TextSpan."
            )

        try:
            iterator = iter(spans)
        except TypeError as exc:
            raise TypeError(
                "TinyTextDetector spans must be "
                "an iterable of TextSpan."
            ) from exc

        evidences: list[
            PromptInjectionEvidence
        ] = []

        for span in iterator:
            if not isinstance(
                span,
                TextSpan,
            ):
                raise TypeError(
                    "TinyTextDetector expects "
                    "TextSpan instances."
                )

            evidence = (
                self._analyze_span(
                    span
                )
            )

            if evidence is not None:
                evidences.append(
                    evidence
                )

        return tuple(
            evidences
        )

    def _analyze_span(
        self,
        span: TextSpan,
    ) -> PromptInjectionEvidence | None:
        text = span.text

        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "TextSpan text must be a string."
            )

        normalized_text = (
            " ".join(
                text.split()
            )
        )

        if not normalized_text:
            return None

        font = span.font

        if font is None:
            return None

        font_size = font.size

        if (
            isinstance(font_size, bool)
            or not isinstance(
                font_size,
                (int, float),
            )
        ):
            raise TypeError(
                "TextSpan font size must be numeric."
            )

        normalized_font_size = float(
            font_size
        )

        # O valor exatamente igual ao limite não é
        # considerado anormalmente pequeno.
        if (
            normalized_font_size
            >= self._maximum_font_size
        ):
            return None

        confidence = (
            self._calculate_confidence(
                font_size=(
                    normalized_font_size
                )
            )
        )

        font_name = getattr(
            font,
            "name",
            None,
        )

        color = getattr(
            font,
            "color",
            None,
        )

        metadata = {
            "font_size": (
                normalized_font_size
            ),
            "font_name": (
                font_name
            ),
            "maximum_font_size": (
                self._maximum_font_size
            ),
            "analysis_method": (
                "font_size_threshold"
            ),
            "detector_version": 1,
        }

        if color is not None:
            to_hex = getattr(
                color,
                "to_hex",
                None,
            )

            if callable(to_hex):
                metadata[
                    "font_color"
                ] = to_hex()

        return PromptInjectionEvidence(
            code=self.EVIDENCE_CODE,
            detector=self.name,
            description=(
                "Foi identificado conteúdo textual "
                "renderizado com tamanho de fonte "
                "anormalmente pequeno, característica "
                "compatível com possível tentativa de "
                "ocultação visual."
            ),
            confidence=confidence,
            weight=0.60,
            page_number=(
                span.page_number
            ),
            original_excerpt=(
                normalized_text[:500]
            ),
            normalized_excerpt=(
                normalized_text[:500]
            ),
            language=None,
            category=self.CATEGORY,
            metadata=metadata,
        )

    def _calculate_confidence(
        self,
        *,
        font_size: float,
    ) -> float:
        """
        A confiança representa a força da anomalia
        tipográfica, não a probabilidade de Prompt Injection.

        Quanto menor a fonte em relação ao threshold,
        mais forte é a evidência de possível ocultação.
        """

        ratio = (
            font_size
            / self._maximum_font_size
        )

        if ratio <= 0.25:
            return 0.98

        if ratio <= 0.50:
            return 0.92

        if ratio <= 0.75:
            return 0.82

        return 0.70