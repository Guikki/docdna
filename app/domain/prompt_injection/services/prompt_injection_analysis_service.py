from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from math import isfinite

from app.domain.services.encoded_content_inspector import (
    EncodedContentInspector,
)

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
        encoded_content_inspector: EncodedContentInspector | None = None,
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

        # CF-QA 003.9.2: conteúdo QR é sempre dado externo, nunca instrução.
        self._encoded_content_inspector = (
            encoded_content_inspector or EncodedContentInspector()
        )

    def analyze(
        self,
        *,
        native_text: Any = None,
        ocr: Any = None,
        normalized_document: Any = None,
        barcodes: Iterable[Any] = (),
        qr_structural_findings: Iterable[dict[str, Any]] = (),
    ) -> PromptInjectionAssessment:
        """
        Executa a investigação em todas as fontes
        e sinais atualmente disponíveis.
        """

        evidences: list[
            PromptInjectionEvidence
        ] = []

        # Materializa uma só vez: entradas podem ser geradores.
        barcode_items = list(barcodes or ())
        structural_items = list(qr_structural_findings or ())

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
                normalized_document,
                qr_structural_findings=structural_items,
            )
        )

        # Analisa o significado do QR, mesmo quando sua representação
        # gráfica foi reconhecida e deixou de gerar alerta de fonte pequena.
        evidences.extend(self._analyze_encoded_sources(
            barcodes=barcode_items,
            qr_structural_findings=structural_items,
        ))

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
        *,
        qr_structural_findings: Iterable[dict[str, Any]] = (),
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

            # Só remove da análise TIPOGRÁFICA os fragmentos binários
            # cuja posição e fonte coincidem com um QR visual decodificado.
            # O conteúdo bruto permanece em qr_structural_findings; o
            # payload decodificado continua submetido à análise semântica.
            filtered_spans = [
                span for span in spans
                if not self._span_is_qr_graphics(
                    span=span,
                    page_number=self._page_number(page),
                    structural_findings=qr_structural_findings,
                )
            ]
            tiny_text_evidences = (
                self._tiny_text_detector.detect(
                    spans=filtered_spans
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

    # CF-QA 003.9.2 — semântica de conteúdos codificados, com origem rastreável.
    def _analyze_encoded_sources(
        self,
        *,
        barcodes: Iterable[Any],
        qr_structural_findings: Iterable[dict[str, Any]],
    ) -> tuple[PromptInjectionEvidence, ...]:
        inspector = self._encoded_content_inspector
        candidates = inspector.prepare_qr_semantic_inputs(barcodes)

        for group in qr_structural_findings:
            if not isinstance(group, dict):
                continue
            decoded = group.get("decoded_content", ())
            if not isinstance(decoded, (list, tuple)):
                continue
            for variant in decoded[:6]:
                if not isinstance(variant, dict):
                    continue
                candidates.append({
                    "source": "QR_FONT_DECODED_TEXT",
                    "page_number": group.get("page_number"),
                    "barcode_index": None,
                    "text": variant.get("text"),
                    "sha256": variant.get("sha256"),
                    "encoding_chain": variant.get("encoding_chain", []),
                    "status": "REQUIRES_SEMANTIC_ANALYSIS",
                    "untrusted": True,
                    "structural_sha256": group.get("raw_sha256"),
                })

        evidences: list[PromptInjectionEvidence] = []
        seen: set[tuple[Any, ...]] = set()
        for candidate in candidates[:inspector.MAX_CANDIDATES]:
            if candidate.get("status") != "REQUIRES_SEMANTIC_ANALYSIS":
                continue
            text = candidate.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            if len(text) > inspector.MAX_RAW_CHARS:
                continue
            source = str(candidate.get("source") or "QR_DECODED_PAYLOAD")
            page = candidate.get("page_number")
            if type(page) is not int or page < 1:
                page = None
            chain = candidate.get("encoding_chain", ())
            if not isinstance(chain, (tuple, list)):
                chain = ()
            chain = tuple(str(item) for item in chain[:inspector.MAX_DEPTH])
            identity = (source, page, candidate.get("barcode_index"),
                        candidate.get("sha256"), chain)
            if identity in seen:
                continue
            seen.add(identity)
            metadata = {
                "barcode_index": candidate.get("barcode_index"),
                "encoded_sha256": candidate.get("sha256"),
                "encoding_chain": list(chain),
                "structural_sha256": candidate.get("structural_sha256"),
                "untrusted": True,
            }
            # Os detectores existentes recebem conteúdo como dado de entrada.
            # Nenhum texto decodificado é executado ou passado como comando.
            for evidence in self._run_text_detectors(
                text=text, source=source.lower(), page_number=page,
                extra_context=metadata,
            ):
                evidences.append(self._with_source_metadata(
                    evidence=evidence, source=source.lower(),
                    extra_metadata=metadata,
                ))
        return tuple(evidences)

    @classmethod
    def _span_is_qr_graphics(
        cls, *, span: Any, page_number: int,
        structural_findings: Iterable[dict[str, Any]],
    ) -> bool:
        text = getattr(span, "text", "")
        if not isinstance(text, str) or len(text.strip()) < 32:
            return False
        if not text.strip() or any(ch not in "01 \t\r\n" for ch in text):
            return False
        # TextSpan normalizado guarda a fonte em span.font.name (objeto Font).
        # Alguns adaptadores e testes antigos expõem font_name diretamente.
        # Nunca converter o objeto Font inteiro em str: isso gera a sua
        # representação, e não o nome comparável com o registro estrutural.
        font_value = getattr(span, "font_name", None)
        if not isinstance(font_value, str) or not font_value.strip():
            font_obj = getattr(span, "font", None)
            font_value = getattr(font_obj, "name", None)
            if not isinstance(font_value, str) and isinstance(font_obj, str):
                font_value = font_obj
        font = font_value.strip() if isinstance(font_value, str) else ""
        bbox = cls._span_bounds(span)
        if not font or bbox is None:
            return False
        for group in structural_findings:
            if not isinstance(group, dict):
                continue
            if group.get("code") != "QR_STRUCTURAL_SPATIAL_ASSOCIATION":
                continue
            if not group.get("linked_qr_codes"):
                continue
            if group.get("page_number") != page_number:
                continue
            if str(group.get("font_name") or "").casefold() != font.casefold():
                continue
            box = group.get("bounding_box_pdf_points")
            try:
                left, top, right, bottom = (float(i) for i in box)
            except (TypeError, ValueError):
                continue
            if not all(isfinite(i) for i in (left, top, right, bottom)):
                continue
            # Centro do span estritamente dentro da região estrutural.
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            if left <= cx <= right and top <= cy <= bottom:
                return True
        return False

    @staticmethod
    def _span_bounds(span: Any) -> tuple[float, float, float, float] | None:
        box = getattr(span, "bounding_box", None)
        if box is None:
            location = getattr(span, "location", None)
            box = getattr(location, "bounding_box", None)
        if box is None:
            return None
        try:
            if isinstance(box, (list, tuple)):
                x0, y0, x1, y1 = (float(i) for i in box)
            elif all(hasattr(box, name) for name in ("left", "top", "right", "bottom")):
                # Contrato do BoundingBox do dominio documental: bordas.
                # O NativeTextSpanAdapter preserva as coordenadas do PyMuPDF.
                x0 = float(box.left)
                y0 = float(box.top)
                x1 = float(box.right)
                y1 = float(box.bottom)
            else:
                # Compatibilidade com adaptadores legados: posicao e tamanho.
                x = float(getattr(box, "x"))
                y = float(getattr(box, "y"))
                x0, y0 = x, y
                x1 = x + float(getattr(box, "width"))
                y1 = y + float(getattr(box, "height"))
            if not all(isfinite(i) for i in (x0, y0, x1, y1)):
                return None
            return (x0, y0, x1, y1) if x0 < x1 and y0 < y1 else None
        except (AttributeError, TypeError, ValueError):
            return None

    def _run_text_detectors(
        self,
        *,
        text: str,
        source: str,
        page_number: int | None,
        extra_context: dict[str, Any] | None = None,
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

        if extra_context:
            context.update(extra_context)

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
        extra_metadata: dict[str, Any] | None = None,
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
            **(extra_metadata or {}),
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

        seen: set[tuple[Any, ...]] = set()

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
                evidence.metadata.get("barcode_index"),
                evidence.metadata.get("encoded_sha256"),
                tuple(evidence.metadata.get("encoding_chain") or ()),
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