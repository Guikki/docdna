from __future__ import annotations

from pathlib import Path

from app.domain.concealment.detectors.low_contrast_text_detector import (
    LowContrastTextDetector,
)
from app.domain.concealment.detectors.white_text_detector import (
    WhiteTextDetector,
)
from app.domain.concealment.models.text_concealment_finding import (
    TextConcealmentFinding,
)
from app.domain.concealment.models.visual_concealment_analysis import (
    VisualConcealmentAnalysis,
)
from app.domain.concealment.services.local_background_color_sampler import (
    LocalBackgroundColorSampler,
)
from app.domain.document.models.document import Document
from app.domain.document.models.text_span import TextSpan
from app.domain.prompt_injection.detectors.tiny_text_detector import (
    TinyTextDetector,
)


class VisualConcealmentAnalysisService:
    """
    Orquestra os detectores de possíveis sinais de ocultação visual textual.

    A cor branca ou quase branca da fonte é tratada inicialmente como um
    dado objetivo. Quando o PDF de origem está disponível, o serviço utiliza
    o contraste local entre texto e fundo para decidir se esse dado deve ser
    promovido a um achado de possível ocultação visual.

    Assim, texto branco claramente visível sobre fundo escuro não é tratado
    como ocultação apenas em razão da cor da fonte.

    Quando não é possível estimar o fundo de forma confiável, o comportamento
    permanece conservador e o achado de texto branco é preservado.
    """

    def __init__(
        self,
        *,
        white_text_detector: WhiteTextDetector | None = None,
        low_contrast_text_detector: LowContrastTextDetector | None = None,
        tiny_text_detector: TinyTextDetector | None = None,
        background_sampler: LocalBackgroundColorSampler | None = None,
    ) -> None:
        self._white_text_detector = (
            white_text_detector or WhiteTextDetector()
        )

        self._background_sampler = (
            background_sampler
            or LocalBackgroundColorSampler()
        )

        self._low_contrast_text_detector = (
            low_contrast_text_detector
            or LowContrastTextDetector(
                background_sampler=self._background_sampler,
            )
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

        # O detector de texto branco identifica apenas a característica
        # objetiva da cor da fonte. A relevância para ocultação visual
        # será avaliada posteriormente quando houver PDF disponível.
        white_text_candidates = tuple(
            self._white_text_detector.detect(document)
        )

        white_text_findings = (
            white_text_candidates
        )

        low_contrast_text_findings = ()

        if pdf_path is not None:
            low_contrast_text_findings = tuple(
                self._low_contrast_text_detector.detect(
                    document,
                    pdf_path=pdf_path,
                )
            )

            white_text_findings = (
                self._select_concealment_relevant_white_text_findings(
                    document=document,
                    findings=white_text_candidates,
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

    def _select_concealment_relevant_white_text_findings(
        self,
        *,
        document: Document,
        findings: tuple[
            TextConcealmentFinding,
            ...,
        ],
        pdf_path: str,
    ) -> tuple[
        TextConcealmentFinding,
        ...,
    ]:
        """
        Mantém como achado apenas o texto branco cuja visibilidade não possa
        ser descartada como normal por meio da análise de contraste local.

        Regras:

        - alto contraste conhecido:
          o texto é claramente visível e não é promovido a ocultação;

        - baixo contraste:
          o achado permanece;

        - fundo indeterminado:
          o achado permanece por prudência;

        - PDF indisponível para inspeção:
          o comportamento anterior é preservado.
        """

        if not findings:
            return ()

        normalized_pdf_path = (
            pdf_path.strip()
            if isinstance(pdf_path, str)
            else ""
        )

        if not normalized_pdf_path:
            return findings

        # Quando um detector substituto é utilizado em testes ou integrações,
        # o caminho pode não representar um arquivo físico. Nesse caso não
        # removemos evidências por falta de contexto visual.
        if not Path(normalized_pdf_path).is_file():
            return findings

        selected_findings: list[
            TextConcealmentFinding
        ] = []

        for finding in findings:
            span = self._find_source_span(
                document=document,
                finding=finding,
            )

            if span is None:
                # Não descartamos um achado se não conseguimos reconstruir
                # de forma segura o TextSpan que lhe deu origem.
                selected_findings.append(
                    finding
                )
                continue

            background = (
                self._background_sampler.sample(
                    pdf_path=normalized_pdf_path,
                    span=span,
                )
            )

            if background is None:
                # Fundo visualmente complexo ou sem predominância suficiente.
                # A incerteza não deve ser usada para suprimir evidência.
                selected_findings.append(
                    finding
                )
                continue

            contrast_ratio = (
                span.font.color.contrast_ratio(
                    background.color
                )
            )

            contrast_threshold = (
                self._white_text_concealment_threshold()
            )

            if contrast_ratio < contrast_threshold:
                selected_findings.append(
                    finding
                )

        return tuple(
            selected_findings
        )

    def _white_text_concealment_threshold(
        self,
    ) -> float:
        """
        Usa a mesma régua técnica adotada pelo detector de baixo contraste.

        Isso evita que o DocDNA utilize dois critérios diferentes para
        interpretar o mesmo fenômeno visual.
        """

        threshold = getattr(
            self._low_contrast_text_detector,
            "low_contrast_threshold",
            (
                LowContrastTextDetector
                .DEFAULT_LOW_CONTRAST_THRESHOLD
            ),
        )

        return float(
            threshold
        )

    @staticmethod
    def _find_source_span(
        *,
        document: Document,
        finding: TextConcealmentFinding,
    ) -> TextSpan | None:
        """
        Localiza o TextSpan nativo que originou um achado de texto branco.

        A associação utiliza página, conteúdo e bounding box, preservando a
        rastreabilidade entre a evidência analítica e o dado documental.
        """

        for page in document.pages:
            for span in page.text_spans:
                if (
                    span.page_number
                    != finding.page_number
                ):
                    continue

                if span.text != finding.text:
                    continue

                if (
                    span.bounding_box
                    != finding.bounding_box
                ):
                    continue

                return span

        return None