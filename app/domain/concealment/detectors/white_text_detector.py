from __future__ import annotations

import re
from statistics import median

from app.domain.concealment.models.text_concealment_finding import (
    TextConcealmentFinding,
)
from app.domain.document.models.document import Document
from app.domain.document.models.page import Page
from app.domain.document.models.text_span import TextSpan


class WhiteTextDetector:
    """
    Detecta texto nativo cuja cor é branca ou quase branca.

    O detector é independente de Prompt Injection.

    Nesta etapa ele avalia a cor objetiva da fonte. A confirmação de baixo
    contraste com o fundo deve pertencer a um detector específico de contraste.
    """

    CODE = "near_white_text"
    NAME = "white_text_detector"

    ABSOLUTE_SMALL_FONT_MAX = 6.5
    RELATIVE_SMALL_FONT_RATIO = 0.60
    NEAR_WHITE_CHANNEL_MIN = 245

    _INSTRUCTION_PATTERNS = (
        r"\bverifique\b",
        r"\bconfira\b",
        r"\binforme\b",
        r"\bresponda\b",
        r"\bdiga\b",
        r"\bignore\b",
        r"\bconsidere\b",
        r"\bmarque\b",
        r"\buse\b",
        r"\bfaça\b",
        r"\bfaca\b",
        r"\bn[aã]o\s+(?:considere|informe|responda|use)\b",
        r"\bse\s+.*\b(?:correto|correta|verdadeiro|verdadeira)\b",
    )

    def detect(
        self,
        document: Document,
    ) -> list[TextConcealmentFinding]:
        if not isinstance(document, Document):
            raise TypeError(
                "WhiteTextDetector document must be a Document."
            )

        findings: list[TextConcealmentFinding] = []

        for page in document.pages:
            page_median = self._page_median_font_size(page)

            for span in page.text_spans:
                finding = self._analyze_span(
                    span=span,
                    page_median=page_median,
                )

                if finding is not None:
                    findings.append(finding)

        return findings

    def _analyze_span(
        self,
        *,
        span: TextSpan,
        page_median: float | None,
    ) -> TextConcealmentFinding | None:
        if not span.text.strip():
            return None

        is_near_white = all(
            channel >= self.NEAR_WHITE_CHANNEL_MIN
            for channel in span.font.color.rgb255
        )

        if not is_near_white:
            return None

        is_small_text = (
            span.font.size <= self.ABSOLUTE_SMALL_FONT_MAX
        )

        is_relative_small_text = False
        if page_median is not None and page_median > 0.0:
            is_relative_small_text = (
                span.font.size
                <= page_median * self.RELATIVE_SMALL_FONT_RATIO
            )

        is_instruction_like = self._looks_like_instruction(span.text)

        signals: list[str] = ["near_white_font"]
        confidence = 0.60

        if is_small_text:
            signals.append("small_font")
            confidence += 0.15

        if is_relative_small_text:
            signals.append("font_smaller_than_page_pattern")
            confidence += 0.10

        if is_instruction_like:
            signals.append("instruction_like_text")
            confidence += 0.15

        return TextConcealmentFinding(
            code=self.CODE,
            detector=self.NAME,
            page_number=span.page_number,
            text=span.text,
            bounding_box=span.bounding_box,
            font_name=span.font.name,
            font_size=span.font.size,
            font_color_hex=span.font.color.to_hex(),
            confidence=min(round(confidence, 4), 1.0),
            signals=tuple(signals),
            is_near_white=True,
            is_small_text=is_small_text,
            is_relative_small_text=is_relative_small_text,
            is_instruction_like=is_instruction_like,
        )

    @staticmethod
    def _page_median_font_size(page: Page) -> float | None:
        sizes = [
            span.font.size
            for span in page.text_spans
            if span.text.strip() and span.font.size > 0.0
        ]

        if not sizes:
            return None

        return float(median(sizes))

    def _looks_like_instruction(self, text: str) -> bool:
        normalized = " ".join(text.casefold().split())

        return any(
            re.search(pattern, normalized) is not None
            for pattern in self._INSTRUCTION_PATTERNS
        )