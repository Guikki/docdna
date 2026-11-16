from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.domain.prompt_injection.detectors.instruction_intent_detector import (
    InstructionIntentDetector,
)
from app.domain.prompt_injection.detectors.prompt_phrase_detector import (
    PromptPhraseDetector,
)
from app.domain.prompt_injection.detectors.tiny_text_detector import (
    TinyTextDetector,
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
    Orquestra a investigação de possíveis tentativas
    de Prompt Injection utilizando fontes e sinais
    independentes.

    Fontes textuais analisadas:

    - texto nativo do PDF;
    - resultado do OCR;
    - documento normalizado por páginas.

    Sinais visuais atualmente analisados:

    - texto com fonte anormalmente pequena.

    Os resultados são consolidados em um único
    PromptInjectionAssessment.

    Este serviço não declara fraude nem autenticidade.
    """

    def __init__(
        self,
        *,
        phrase_detector: PromptPhraseDetector | None = None,
        instruction_intent_detector: (
            InstructionIntentDetector | None
        ) = None,
        tiny_text_detector: TinyTextDetector | None = None,
        assessment_builder: (
            PromptInjectionAssessmentBuilder | None
        ) = None,
    ) -> None:
        self._phrase_detector = (
            phrase_detector
            if phrase_detector is not None
            else PromptPhraseDetector()
        )

        self._instruction_intent_detector = (
            instruction_intent_detector
            if instruction_intent_detector is not None
            else InstructionIntentDetector()
        )

        self._tiny_text_detector = (
            tiny_text_detector
            if tiny_text_detector is not None
            else TinyTextDetector()
        )

        self._assessment_builder = (
            assessment_builder
            if assessment_builder is not None
            else PromptInjectionAssessmentBuilder()
        )

    def analyze(
        self,
        *,
        native_text: Any = None,
        ocr: Any = None,
        normalized_document: Any = None,
    ) -> PromptInjectionAssessment:
        """
        Executa a investigação em todas as fontes
        e sinais atualmente disponíveis.
        """

        evidences: list[
            PromptInjectionEvidence
        ] = []

        evidences.extend(
            self._analyze_native_text(
                native_text
            )
        )

        evidences.extend(
            self._analyze_ocr(
                ocr
            )
        )

        evidences.extend(
            self._analyze_normalized_document_text(
                normalized_document
            )
        )

        evidences.extend(
            self._analyze_tiny_text(
                normalized_document
            )
        )

        unique_evidences = (
            self._deduplicate_evidences(
                evidences
            )
        )

        return self._assessment_builder.build(
            unique_evidences
        )

    def _analyze_native_text(
        self,
        native_text: Any,
    ) -> tuple[
        PromptInjectionEvidence,
        ...
    ]:
        if native_text is None:
            return ()

        content = getattr(
            native_text,
            "content",
            "",
        )

        if not isinstance(
            content,
            str,
        ):
            raise TypeError(
                "Native text content must be a string."
            )

        if not content.strip():
            return ()

        return self._run_text_detectors(
            text=content,
            source="native_text",
            page_number=None,
        )

    def _analyze_ocr(
        self,
        ocr: Any,
    ) -> tuple[
        PromptInjectionEvidence,
        ...
    ]:
        if ocr is None:
            return ()

        page_results = (
            self._extract_ocr_pages(
                ocr
            )
        )

        if page_results:
            evidences: list[
                PromptInjectionEvidence
            ] = []

            for (
                page_number,
                page_text,
            ) in page_results:
                if not page_text.strip():
                    continue

                evidences.extend(
                    self._run_text_detectors(
                        text=page_text,
                        source="ocr",
                        page_number=page_number,
                    )
                )

            return tuple(
                evidences
            )

        content = getattr(
            ocr,
            "content",
            "",
        )

        if not isinstance(
            content,
            str,
        ):
            raise TypeError(
                "OCR content must be a string."
            )

        if not content.strip():
            return ()

        return self._run_text_detectors(
            text=content,
            source="ocr",
            page_number=None,
        )

    def _analyze_normalized_document_text(
        self,
        normalized_document: Any,
    ) -> tuple[
        PromptInjectionEvidence,
        ...
    ]:
        if normalized_document is None:
            return ()

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
            page_number = (
                self._page_number(
                    page
                )
            )

            page_text = (
                self._page_text(
                    page
                )
            )

            if not page_text:
                continue

            evidences.extend(
                self._run_text_detectors(
                    text=page_text,
                    source="normalized_document",
                    page_number=page_number,
                )
            )

        return tuple(
            evidences
        )

    def _analyze_tiny_text(
        self,
        normalized_document: Any,
    ) -> tuple[
        PromptInjectionEvidence,
        ...
    ]:
        """
        Executa a análise tipográfica sobre os TextSpan
        do documento normalizado.

        Cada evidência produzida pelo TinyTextDetector recebe
        a origem 'normalized_document_visual' para diferenciá-la
        das evidências puramente textuais.
        """

        if normalized_document is None:
            return ()

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
            spans = getattr(
                page,
                "text_spans",
                None,
            )

            if spans is None:
                continue

            tiny_text_evidences = (
                self._tiny_text_detector.detect(
                    spans=spans
                )
            )

            for evidence in tiny_text_evidences:
                evidences.append(
                    self._with_source_metadata(
                        evidence=evidence,
                        source=(
                            "normalized_document_visual"
                        ),
                    )
                )

        return tuple(
            evidences
        )

    def _run_text_detectors(
        self,
        *,
        text: str,
        source: str,
        page_number: int | None,
    ) -> tuple[
        PromptInjectionEvidence,
        ...
    ]:
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "Prompt Injection analysis text "
                "must be a string."
            )

        if not text.strip():
            return ()

        context: dict[
            str,
            Any,
        ] = {
            "source": source,
        }

        if page_number is not None:
            context[
                "page_number"
            ] = page_number

        phrase_evidences = (
            self._phrase_detector.detect(
                text=text,
                context=context,
            )
        )

        intent_evidences = (
            self._instruction_intent_detector.detect(
                text=text,
                context=context,
            )
        )

        return (
            *phrase_evidences,
            *intent_evidences,
        )

    @staticmethod
    def _with_source_metadata(
        *,
        evidence: PromptInjectionEvidence,
        source: str,
    ) -> PromptInjectionEvidence:
        """
        Recria a evidência preservando seus dados e
        acrescentando a origem da análise.

        PromptInjectionEvidence é imutável, então não
        alteramos metadata in-place.
        """

        metadata = {
            **dict(
                evidence.metadata
            ),
            "source": source,
        }

        return PromptInjectionEvidence(
            code=evidence.code,
            detector=evidence.detector,
            description=evidence.description,
            confidence=evidence.confidence,
            weight=evidence.weight,
            page_number=evidence.page_number,
            original_excerpt=(
                evidence.original_excerpt
            ),
            normalized_excerpt=(
                evidence.normalized_excerpt
            ),
            language=evidence.language,
            category=evidence.category,
            start_index=evidence.start_index,
            end_index=evidence.end_index,
            metadata=metadata,
        )

    @staticmethod
    def _extract_ocr_pages(
        ocr: Any,
    ) -> tuple[
        tuple[int, str],
        ...
    ]:
        """
        Tenta utilizar a representação por páginas do OCR
        quando o modelo expuser essa informação.

        Caso não exista, o serviço utilizará o conteúdo
        OCR consolidado.
        """

        candidates = (
            getattr(
                ocr,
                "pages",
                None,
            ),
            getattr(
                ocr,
                "page_results",
                None,
            ),
        )

        pages = next(
            (
                candidate
                for candidate
                in candidates
                if candidate is not None
            ),
            None,
        )

        if pages is None:
            return ()

        result: list[
            tuple[int, str]
        ] = []

        for index, page in enumerate(
            pages,
            start=1,
        ):
            page_number = getattr(
                page,
                "page_number",
                getattr(
                    page,
                    "number",
                    index,
                ),
            )

            if (
                isinstance(
                    page_number,
                    bool,
                )
                or not isinstance(
                    page_number,
                    int,
                )
            ):
                page_number = index

            page_text = getattr(
                page,
                "content",
                getattr(
                    page,
                    "text",
                    "",
                ),
            )

            if isinstance(
                page_text,
                str,
            ):
                result.append(
                    (
                        page_number,
                        page_text,
                    )
                )

        return tuple(
            result
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
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                int,
            )
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
        normalized_text = getattr(
            page,
            "normalized_text",
            None,
        )

        if isinstance(
            normalized_text,
            str,
        ):
            return (
                normalized_text.strip()
            )

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
                isinstance(
                    span_text,
                    str,
                )
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
        Deduplica evidências equivalentes dentro da mesma
        origem de análise.

        A mesma instrução encontrada em:

        - texto nativo;
        - OCR;
        - documento normalizado;
        - análise visual;

        permanece como evidência independente de
        corroboração.
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
                str | None,
            ]
        ] = set()

        for evidence in evidences:
            source = (
                evidence.metadata.get(
                    "source"
                )
            )

            identity = (
                evidence.code,
                evidence.language,
                evidence.category,
                evidence.page_number,
                evidence.normalized_excerpt,
                source,
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