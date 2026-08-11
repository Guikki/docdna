from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.domain.prompt_injection.detectors.prompt_phrase_detector import (
    PromptPhraseDetector,
)
from app.domain.prompt_injection.models.prompt_injection_assessment import (
    PromptInjectionAssessment,
)
from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)
from app.domain.prompt_injection.services.prompt_injection_assessment_builder import (
    PromptInjectionAssessmentBuilder,
)


class PromptInjectionAnalysisService:
    """
    Orquestra a análise textual de possíveis tentativas
    de Prompt Injection em um documento normalizado.

    Responsabilidades:

    - percorrer as páginas do documento;
    - executar os detectores textuais;
    - preservar o número da página;
    - remover evidências duplicadas;
    - construir um PromptInjectionAssessment único.

    O serviço não interpreta autenticidade documental.
    """

    def __init__(
        self,
        *,
        phrase_detector: PromptPhraseDetector | None = None,
        assessment_builder: (
            PromptInjectionAssessmentBuilder | None
        ) = None,
    ) -> None:
        self._phrase_detector = (
            phrase_detector
            if phrase_detector is not None
            else PromptPhraseDetector()
        )

        self._assessment_builder = (
            assessment_builder
            if assessment_builder is not None
            else PromptInjectionAssessmentBuilder()
        )

    def analyze(
        self,
        *,
        normalized_document: Any,
    ) -> PromptInjectionAssessment:
        """
        Analisa todas as páginas de um documento normalizado.
        """

        if normalized_document is None:
            return self._assessment_builder.build(
                ()
            )

        pages = getattr(
            normalized_document,
            "pages",
            None,
        )

        if pages is None:
            raise TypeError(
                "PromptInjectionAnalysisService "
                "normalized_document must expose pages."
            )

        evidences: list[
            PromptInjectionEvidence
        ] = []

        for page in pages:
            page_number = self._page_number(
                page
            )

            page_text = self._page_text(
                page
            )

            if not page_text:
                continue

            page_evidences = (
                self._phrase_detector.detect(
                    text=page_text,
                    context={
                        "page_number": page_number,
                        "source": (
                            "normalized_document"
                        ),
                    },
                )
            )

            evidences.extend(
                page_evidences
            )

        unique_evidences = (
            self._deduplicate_evidences(
                evidences
            )
        )

        return self._assessment_builder.build(
            unique_evidences
        )

    @staticmethod
    def _page_number(
        page: Any,
    ) -> int:
        value = getattr(
            page,
            "number",
            None,
        )

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise TypeError(
                "Normalized document page number "
                "must be an integer."
            )

        if value < 1:
            raise ValueError(
                "Normalized document page number "
                "must be greater than or equal to 1."
            )

        return value

    @staticmethod
    def _page_text(
        page: Any,
    ) -> str:
        """
        Obtém o conteúdo textual consolidado da página.

        Preferimos normalized_text quando disponível.
        Caso a entidade Page não exponha a propriedade,
        consolidamos os TextSpan.
        """

        normalized_text = getattr(
            page,
            "normalized_text",
            None,
        )

        if isinstance(
            normalized_text,
            str,
        ):
            return normalized_text.strip()

        text_spans = getattr(
            page,
            "text_spans",
            (),
        )

        if not isinstance(
            text_spans,
            Iterable,
        ):
            raise TypeError(
                "Normalized document page "
                "text_spans must be iterable."
            )

        parts: list[str] = []

        for span in text_spans:
            span_text = getattr(
                span,
                "normalized_text",
                None,
            )

            if not isinstance(
                span_text,
                str,
            ):
                span_text = getattr(
                    span,
                    "text",
                    "",
                )

            if (
                isinstance(span_text, str)
                and span_text.strip()
            ):
                parts.append(
                    span_text.strip()
                )

        return " ".join(
            parts
        )

    @staticmethod
    def _deduplicate_evidences(
        evidences: Iterable[
            PromptInjectionEvidence
        ],
    ) -> tuple[
        PromptInjectionEvidence,
        ...
    ]:
        """
        Evita multiplicar o mesmo sinal quando frases de um
        mesmo trecho correspondem a regras equivalentes.
        """

        unique: list[
            PromptInjectionEvidence
        ] = []

        seen: set[
            tuple[
                str,
                str | None,
                str | None,
                int | None,
                str | None,
            ]
        ] = set()

        for evidence in evidences:
            identity = (
                evidence.code,
                evidence.language,
                evidence.category,
                evidence.page_number,
                evidence.normalized_excerpt,
            )

            if identity in seen:
                continue

            seen.add(
                identity
            )

            unique.append(
                evidence
            )

        return tuple(
            unique
        )