from __future__ import annotations

from app.domain.concealment.detectors.low_contrast_text_detector import (
    LowContrastTextDetector,
)
from app.domain.concealment.detectors.white_text_detector import (
    WhiteTextDetector,
)
from app.domain.concealment.models.visual_concealment_analysis import (
    VisualConcealmentAnalysis,
)
from app.domain.document.models.document import Document
from app.domain.prompt_injection.detectors.tiny_text_detector import (
    TinyTextDetector,
)


class VisualConcealmentAnalysisService:
    def __init__(
        self,
        *,
        white_text_detector: WhiteTextDetector | None = None,
        low_contrast_text_detector: LowContrastTextDetector | None = None,
        tiny_text_detector: TinyTextDetector | None = None,
    ) -> None:
        self._white_text_detector = (
            white_text_detector or WhiteTextDetector()
        )
        self._low_contrast_text_detector = (
            low_contrast_text_detector
            or LowContrastTextDetector()
        )
        self._tiny_text_detector = (
            tiny_text_detector or TinyTextDetector()
        )

    def analyze(
        self,
        document: Document,
        *,
        pdf_path: str | None = None,
    ) -> VisualConcealmentAnalysis:
        if not isinstance(document, Document):
            raise TypeError(
                "VisualConcealmentAnalysisService "
                "document must be a Document."
            )

        white_text_findings = (
            self._white_text_detector.detect(document)
        )

        low_contrast_text_findings = ()
        if pdf_path is not None:
            low_contrast_text_findings = tuple(
                self._low_contrast_text_detector.detect(
                    document,
                    pdf_path=pdf_path,
                )
            )

        all_spans = tuple(
            span
            for page in document.pages
            for span in page.text_spans
        )

        tiny_text_evidences = (
            self._tiny_text_detector.detect(
                spans=all_spans
            )
        )

        return VisualConcealmentAnalysis(
            white_text_findings=tuple(
                white_text_findings
            ),
            low_contrast_text_findings=(
                low_contrast_text_findings
            ),
            tiny_text_evidences=tuple(
                tiny_text_evidences
            ),
        )
