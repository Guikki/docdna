from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image, ImageDraw

from app.config.settings import settings
from app.domain.document.models.document import Document
from app.domain.document.models.text_span import TextSpan
from app.domain.models.ocr_text_box import OcrTextBox
from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)
from app.domain.prompt_injection.models.prompt_injection_location import (
    PromptInjectionLocation,
)


class PromptInjectionVisualEvidenceBuilder:
    """
    Localiza visualmente evidências de possível Prompt Injection.

    A estratégia é "native first":

    1. tenta localizar o conteúdo nos TextSpan do documento normalizado;
    2. quando houver localização nativa, preserva bounding box e metadados
       tipográficos objetivos;
    3. somente quando a localização nativa não for possível, utiliza as
       caixas produzidas pelo OCR como fallback;
    4. gera uma imagem anotada para revisão humana.

    A localização não confirma, por si só, que a evidência representa uma
    tentativa real de Prompt Injection.
    """

    LINE_VERTICAL_TOLERANCE = 20
    MINIMUM_CANDIDATE_LENGTH = 4

    # Mantém coerência com o TinyTextDetector atual sem transformar este
    # builder em classificador. O valor serve apenas para metadado visual.
    TINY_TEXT_MAX_SIZE = 4.0

    # O OCR atual renderiza as páginas com Matrix(2, 2). TextSpan nativo,
    # por outro lado, utiliza coordenadas documentais. Antes de desenhar a
    # caixa nativa na imagem renderizada, aplicamos este fator.
    RENDER_SCALE = 2.0

    def build(
        self,
        *,
        pdf_path: str,
        evidences: tuple[PromptInjectionEvidence, ...]
        | list[PromptInjectionEvidence],
        boxes: list[OcrTextBox],
        normalized_document: Document | None = None,
    ) -> list[PromptInjectionLocation]:
        if not isinstance(pdf_path, str):
            raise TypeError(
                "pdf_path must be a string."
            )

        if not isinstance(boxes, list):
            raise TypeError(
                "boxes must be a list."
            )

        if (
            normalized_document is not None
            and not isinstance(
                normalized_document,
                Document,
            )
        ):
            raise TypeError(
                "normalized_document must be a Document or None."
            )

        source_path = Path(pdf_path)

        output_dir = (
            settings.EXTRACTED_DIR
            / source_path.stem
            / "prompt-injection-evidence"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        result: list[PromptInjectionLocation] = []

        for evidence_index, evidence in enumerate(
            evidences,
            start=1,
        ):
            if not isinstance(
                evidence,
                PromptInjectionEvidence,
            ):
                raise TypeError(
                    "evidences must contain only "
                    "PromptInjectionEvidence instances."
                )

            result.append(
                self._locate_evidence(
                    pdf_path=pdf_path,
                    evidence=evidence,
                    evidence_index=evidence_index,
                    boxes=boxes,
                    normalized_document=normalized_document,
                    output_dir=output_dir,
                )
            )

        return result

    def _locate_evidence(
        self,
        *,
        pdf_path: str,
        evidence: PromptInjectionEvidence,
        evidence_index: int,
        boxes: list[OcrTextBox],
        normalized_document: Document | None,
        output_dir: Path,
    ) -> PromptInjectionLocation:
        native_candidates = (
            self._build_native_search_candidates(
                evidence
            )
        )

        if (
            normalized_document is not None
            and native_candidates
        ):
            native_location = (
                self._locate_in_native_document(
                    pdf_path=pdf_path,
                    evidence=evidence,
                    evidence_index=evidence_index,
                    candidates=native_candidates,
                    normalized_document=normalized_document,
                    output_dir=output_dir,
                )
            )

            if native_location is not None:
                return native_location

        ocr_candidates = (
            self._build_ocr_search_candidates(
                evidence
            )
        )

        if not ocr_candidates:
            return self._not_located(
                evidence=evidence,
                evidence_index=evidence_index,
                message=(
                    "A evidência não possui conteúdo textual "
                    "suficiente para localização visual."
                ),
            )

        ocr_location = (
            self._locate_in_ocr_boxes(
                pdf_path=pdf_path,
                evidence=evidence,
                evidence_index=evidence_index,
                candidates=ocr_candidates,
                boxes=boxes,
                output_dir=output_dir,
            )
        )

        if ocr_location is not None:
            return ocr_location

        if normalized_document is not None:
            message = (
                "Não foi possível confirmar visualmente a localização "
                "da evidência nem no texto nativo do documento nem nas "
                "caixas produzidas pelo OCR."
            )
        else:
            message = (
                "Não foi possível confirmar visualmente "
                "a localização da evidência nas caixas "
                "produzidas pelo OCR."
            )

        return self._not_located(
            evidence=evidence,
            evidence_index=evidence_index,
            message=message,
        )

    # ------------------------------------------------------------------
    # LOCALIZAÇÃO NATIVA
    # ------------------------------------------------------------------

    def _locate_in_native_document(
        self,
        *,
        pdf_path: str,
        evidence: PromptInjectionEvidence,
        evidence_index: int,
        candidates: list[str],
        normalized_document: Document,
        output_dir: Path,
    ) -> PromptInjectionLocation | None:
        ordered_pages = (
            self._ordered_native_pages(
                normalized_document=normalized_document,
                preferred_page=evidence.page_number,
            )
        )

        for candidate in candidates:
            for page in ordered_pages:
                matched_spans = (
                    self._find_candidate_in_text_spans(
                        candidate=candidate,
                        spans=list(
                            page.text_spans
                        ),
                    )
                )

                if not matched_spans:
                    continue

                left = min(
                    span.bounding_box.left
                    for span in matched_spans
                )

                top = min(
                    span.bounding_box.top
                    for span in matched_spans
                )

                right = max(
                    span.bounding_box.right
                    for span in matched_spans
                )

                bottom = max(
                    span.bounding_box.bottom
                    for span in matched_spans
                )

                width = right - left
                height = bottom - top

                matched_content = (
                    " ".join(
                        span.text.strip()
                        for span in matched_spans
                        if span.text.strip()
                    )
                )

                representative_span = (
                    self._select_representative_span(
                        matched_spans
                    )
                )

                font = representative_span.font
                font_color_hex = (
                    font.color.to_hex()
                )

                is_tiny_text = (
                    font.size
                    <= self.TINY_TEXT_MAX_SIZE
                )

                is_white_text = (
                    self._is_white_color(
                        font.color.rgb255
                    )
                )

                # TextSpan trabalha em coordenadas documentais.
                # A imagem utilizada pelo renderer é 2x.
                render_left = (
                    left
                    * self.RENDER_SCALE
                )

                render_top = (
                    top
                    * self.RENDER_SCALE
                )

                render_width = (
                    width
                    * self.RENDER_SCALE
                )

                render_height = (
                    height
                    * self.RENDER_SCALE
                )

                (
                    source_image_path,
                    annotated_image_path,
                ) = self._render_annotated_page(
                    pdf_path=pdf_path,
                    page_number=page.number,
                    evidence_index=evidence_index,
                    left=render_left,
                    top=render_top,
                    width=render_width,
                    height=render_height,
                    output_dir=output_dir,
                )

                return PromptInjectionLocation(
                    evidence_index=evidence_index,
                    evidence_code=evidence.code,
                    detector=evidence.detector,
                    page_number=page.number,
                    matched_content=matched_content,
                    left=left,
                    top=top,
                    width=width,
                    height=height,
                    confidence=evidence.confidence,
                    source_image_path=str(
                        source_image_path
                    ),
                    annotated_image_path=str(
                        annotated_image_path
                    ),
                    located=True,
                    message=(
                        "O conteúdo associado à evidência foi "
                        "localizado no texto nativo do documento."
                    ),
                    source="native_text",
                    font_name=font.name,
                    font_size=font.size,
                    font_color_hex=font_color_hex,
                    is_tiny_text=is_tiny_text,
                    is_white_text=is_white_text,
                )

        return None

    def _ordered_native_pages(
        self,
        *,
        normalized_document: Document,
        preferred_page: int | None,
    ) -> list[Any]:
        pages = list(
            normalized_document.pages
        )

        if preferred_page is None:
            return pages

        preferred = [
            page
            for page in pages
            if page.number
            == preferred_page
        ]

        remaining = [
            page
            for page in pages
            if page.number
            != preferred_page
        ]

        return [
            *preferred,
            *remaining,
        ]

    def _find_candidate_in_text_spans(
        self,
        *,
        candidate: str,
        spans: list[TextSpan],
    ) -> list[TextSpan] | None:
        ordered_spans = sorted(
            (
                span
                for span in spans
                if span.text.strip()
            ),
            key=lambda span: (
                span.bounding_box.top,
                span.bounding_box.left,
            ),
        )

        # Primeiro procura dentro de um único span. É o cenário ideal para
        # texto escondido em rodapé, que frequentemente vem como um span
        # próprio no PDF.
        for span in ordered_spans:
            normalized_span = (
                self._normalize_text(
                    span.text
                )
            )

            if (
                candidate
                in normalized_span
            ):
                return [
                    span
                ]

        # Depois permite que a frase atravesse múltiplos spans consecutivos.
        for start_index in range(
            len(
                ordered_spans
            )
        ):
            collected_spans: list[
                TextSpan
            ] = []

            collected_parts: list[
                str
            ] = []

            for current_index in range(
                start_index,
                len(
                    ordered_spans
                ),
            ):
                span = (
                    ordered_spans[
                        current_index
                    ]
                )

                normalized_span = (
                    self._normalize_text(
                        span.text
                    )
                )

                if not normalized_span:
                    continue

                collected_spans.append(
                    span
                )

                collected_parts.append(
                    normalized_span
                )

                combined_text = (
                    " ".join(
                        collected_parts
                    )
                )

                if candidate in combined_text:
                    return collected_spans

                if (
                    len(
                        combined_text.split()
                    )
                    > len(
                        candidate.split()
                    )
                    + 12
                ):
                    break

                if not self._could_still_match(
                    candidate=candidate,
                    collected=combined_text,
                ):
                    break

        return None

    @staticmethod
    def _select_representative_span(
        spans: list[TextSpan],
    ) -> TextSpan:
        """
        Quando vários spans compõem a correspondência, preserva os metadados
        do menor tamanho tipográfico. Isso favorece a característica mais
        relevante em possíveis técnicas de ocultação.
        """
        return min(
            spans,
            key=lambda span: (
                span.font.size,
                span.bounding_box.top,
                span.bounding_box.left,
            ),
        )

    @staticmethod
    def _is_white_color(
        rgb255: tuple[int, int, int],
    ) -> bool:
        red, green, blue = rgb255

        return (
            red >= 250
            and green >= 250
            and blue >= 250
        )

    # ------------------------------------------------------------------
    # LOCALIZAÇÃO OCR
    # ------------------------------------------------------------------

    def _locate_in_ocr_boxes(
        self,
        *,
        pdf_path: str,
        evidence: PromptInjectionEvidence,
        evidence_index: int,
        candidates: list[str],
        boxes: list[OcrTextBox],
        output_dir: Path,
    ) -> PromptInjectionLocation | None:
        boxes_by_page = (
            self._group_boxes_by_page(
                boxes
            )
        )

        preferred_page = (
            evidence.page_number
        )

        ordered_pages = (
            self._ordered_page_numbers(
                boxes_by_page=boxes_by_page,
                preferred_page=preferred_page,
            )
        )

        for candidate in candidates:
            for page_number in ordered_pages:
                page_boxes = (
                    boxes_by_page[
                        page_number
                    ]
                )

                match = (
                    self._find_candidate_match(
                        candidate=candidate,
                        boxes=page_boxes,
                    )
                )

                if match is None:
                    continue

                matched_boxes = match

                left = min(
                    box.left
                    for box in matched_boxes
                )

                top = min(
                    box.top
                    for box in matched_boxes
                )

                right = max(
                    box.left
                    + box.width
                    for box in matched_boxes
                )

                bottom = max(
                    box.top
                    + box.height
                    for box in matched_boxes
                )

                width = (
                    right
                    - left
                )

                height = (
                    bottom
                    - top
                )

                confidence = (
                    sum(
                        float(
                            box.confidence
                        )
                        for box
                        in matched_boxes
                    )
                    / len(
                        matched_boxes
                    )
                )

                matched_content = (
                    " ".join(
                        box.text
                        for box
                        in matched_boxes
                        if box.text.strip()
                    )
                )

                (
                    source_image_path,
                    annotated_image_path,
                ) = self._render_annotated_page(
                    pdf_path=pdf_path,
                    page_number=page_number,
                    evidence_index=evidence_index,
                    left=left,
                    top=top,
                    width=width,
                    height=height,
                    output_dir=output_dir,
                )

                return PromptInjectionLocation(
                    evidence_index=evidence_index,
                    evidence_code=evidence.code,
                    detector=evidence.detector,
                    page_number=page_number,
                    matched_content=matched_content,
                    left=left,
                    top=top,
                    width=width,
                    height=height,
                    confidence=confidence,
                    source_image_path=str(
                        source_image_path
                    ),
                    annotated_image_path=str(
                        annotated_image_path
                    ),
                    located=True,
                    message=(
                        "O conteúdo associado à evidência "
                        "foi localizado visualmente nas "
                        "caixas produzidas pelo OCR."
                    ),
                    source="ocr",
                    font_name=None,
                    font_size=None,
                    font_color_hex=None,
                    is_tiny_text=None,
                    is_white_text=None,
                )

        return None

    # ------------------------------------------------------------------
    # CANDIDATOS
    # ------------------------------------------------------------------

    def _build_native_search_candidates(
        self,
        evidence: PromptInjectionEvidence,
    ) -> list[str]:
        """
        Para localização nativa, prioriza trechos longos e específicos da
        própria evidência.

        Sinais isolados são deliberadamente evitados aqui para impedir que
        palavras genéricas, como "correspondente", sejam tratadas como a
        localização do Prompt Injection.
        """
        result: list[str] = []

        self._append_excerpt_windows(
            result,
            evidence.original_excerpt,
            window_sizes=(
                24,
                16,
                12,
                8,
                5,
            ),
        )

        self._append_excerpt_windows(
            result,
            evidence.normalized_excerpt,
            window_sizes=(
                24,
                16,
                12,
                8,
                5,
            ),
        )

        metadata = getattr(
            evidence,
            "metadata",
            {},
        )

        matched_rule = (
            metadata.get(
                "matched_rule"
            )
        )

        if isinstance(
            matched_rule,
            str,
        ):
            normalized_rule = (
                self._normalize_text(
                    matched_rule
                )
            )

            # Regra curta demais não deve apontar uma posição nativa sozinha.
            if (
                len(
                    normalized_rule.split()
                )
                >= 2
            ):
                self._append_candidate(
                    result,
                    matched_rule,
                )

        matched_signals = (
            metadata.get(
                "matched_signals",
                {},
            )
        )

        if isinstance(
            matched_signals,
            dict,
        ):
            signals: list[str] = []

            for values in (
                matched_signals.values()
            ):
                if isinstance(
                    values,
                    str,
                ):
                    signals.append(
                        values
                    )
                    continue

                try:
                    iterator = iter(
                        values
                    )
                except TypeError:
                    continue

                for signal in iterator:
                    if isinstance(
                        signal,
                        str,
                    ):
                        signals.append(
                            signal
                        )

            signals.sort(
                key=lambda value: (
                    len(
                        self._normalize_text(
                            value
                        ).split()
                    ),
                    len(value),
                ),
                reverse=True,
            )

            for signal in signals:
                normalized_signal = (
                    self._normalize_text(
                        signal
                    )
                )

                # Evita palavra genérica isolada. Sinais de uma palavra não
                # são suficientemente específicos para localização nativa.
                if (
                    len(
                        normalized_signal.split()
                    )
                    < 2
                ):
                    continue

                self._append_candidate(
                    result,
                    signal,
                )

        return result

    def _build_ocr_search_candidates(
        self,
        evidence: PromptInjectionEvidence,
    ) -> list[str]:
        """
        Mantém compatibilidade com a estratégia OCR existente, mas tenta
        trechos da própria evidência antes dos sinais individuais.
        """
        result: list[str] = []

        self._append_excerpt_windows(
            result,
            evidence.original_excerpt,
            window_sizes=(
                12,
                8,
                5,
            ),
        )

        self._append_excerpt_windows(
            result,
            evidence.normalized_excerpt,
            window_sizes=(
                8,
                5,
            ),
        )

        metadata = getattr(
            evidence,
            "metadata",
            {},
        )

        matched_rule = (
            metadata.get(
                "matched_rule"
            )
        )

        if isinstance(
            matched_rule,
            str,
        ):
            self._append_candidate(
                result,
                matched_rule,
            )

        matched_signals = (
            metadata.get(
                "matched_signals",
                {},
            )
        )

        if isinstance(
            matched_signals,
            dict,
        ):
            flattened_signals: list[str] = []

            for signals in (
                matched_signals.values()
            ):
                if isinstance(
                    signals,
                    str,
                ):
                    flattened_signals.append(
                        signals
                    )
                    continue

                try:
                    iterator = iter(
                        signals
                    )
                except TypeError:
                    continue

                for signal in iterator:
                    if isinstance(
                        signal,
                        str,
                    ):
                        flattened_signals.append(
                            signal
                        )

            flattened_signals.sort(
                key=len,
                reverse=True,
            )

            for signal in flattened_signals:
                self._append_candidate(
                    result,
                    signal,
                )

        return result

    # Compatibilidade com possíveis consumidores internos/testes antigos.
    def _build_search_candidates(
        self,
        evidence: PromptInjectionEvidence,
    ) -> list[str]:
        return (
            self._build_ocr_search_candidates(
                evidence
            )
        )

    def _append_excerpt_windows(
        self,
        values: list[str],
        excerpt: Any,
        *,
        window_sizes: tuple[int, ...],
    ) -> None:
        if not isinstance(
            excerpt,
            str,
        ):
            return

        words = excerpt.split()

        if not words:
            return

        for window_size in window_sizes:
            if (
                len(words)
                < window_size
            ):
                continue

            self._append_candidate(
                values,
                " ".join(
                    words[
                        :window_size
                    ]
                ),
            )

        # Se o trecho for menor que todas as janelas, ainda o utiliza.
        smallest_window = min(
            window_sizes
        )

        if (
            len(words)
            < smallest_window
        ):
            self._append_candidate(
                values,
                excerpt,
            )

    def _append_candidate(
        self,
        values: list[str],
        value: str,
    ) -> None:
        normalized = (
            self._normalize_text(
                value
            )
        )

        if (
            len(normalized)
            < self.MINIMUM_CANDIDATE_LENGTH
        ):
            return

        if normalized not in values:
            values.append(
                normalized
            )

    # ------------------------------------------------------------------
    # MATCHING OCR
    # ------------------------------------------------------------------

    def _find_candidate_match(
        self,
        *,
        candidate: str,
        boxes: list[OcrTextBox],
    ) -> list[OcrTextBox] | None:
        visual_lines = (
            self._group_boxes_by_visual_line(
                boxes
            )
        )

        for visual_line in visual_lines:
            match = (
                self._find_in_ordered_boxes(
                    candidate=candidate,
                    boxes=visual_line,
                )
            )

            if match is not None:
                return match

        ordered_page_boxes = sorted(
            boxes,
            key=lambda box: (
                box.top,
                box.left,
            ),
        )

        return self._find_in_ordered_boxes(
            candidate=candidate,
            boxes=ordered_page_boxes,
        )

    def _find_in_ordered_boxes(
        self,
        *,
        candidate: str,
        boxes: list[OcrTextBox],
    ) -> list[OcrTextBox] | None:
        candidate_tokens = (
            candidate.split()
        )

        if not candidate_tokens:
            return None

        normalized_boxes = [
            (
                box,
                self._normalize_text(
                    box.text
                ),
            )
            for box in boxes
            if self._normalize_text(
                box.text
            )
        ]

        for start_index in range(
            len(
                normalized_boxes
            )
        ):
            collected_boxes: list[
                OcrTextBox
            ] = []

            collected_text_parts: list[
                str
            ] = []

            for current_index in range(
                start_index,
                len(
                    normalized_boxes
                ),
            ):
                (
                    box,
                    box_text,
                ) = (
                    normalized_boxes[
                        current_index
                    ]
                )

                collected_boxes.append(
                    box
                )

                collected_text_parts.append(
                    box_text
                )

                combined_text = (
                    " ".join(
                        collected_text_parts
                    )
                )

                if candidate in combined_text:
                    return collected_boxes

                combined_tokens = (
                    combined_text.split()
                )

                if (
                    len(
                        combined_tokens
                    )
                    > len(
                        candidate_tokens
                    )
                    + 5
                ):
                    break

                if not self._could_still_match(
                    candidate=candidate,
                    collected=combined_text,
                ):
                    break

        return None

    def _could_still_match(
        self,
        *,
        candidate: str,
        collected: str,
    ) -> bool:
        if not collected:
            return True

        if candidate.startswith(
            collected
        ):
            return True

        # Se o candidato já está parcialmente contido, ainda vale continuar.
        if collected in candidate:
            return True

        candidate_tokens = (
            candidate.split()
        )

        collected_tokens = (
            collected.split()
        )

        if (
            not candidate_tokens
            or not collected_tokens
        ):
            return False

        comparable_length = min(
            len(
                collected_tokens
            ),
            len(
                candidate_tokens
            ),
        )

        matching_tokens = sum(
            left == right
            for left, right
            in zip(
                collected_tokens[
                    :comparable_length
                ],
                candidate_tokens[
                    :comparable_length
                ],
            )
        )

        if comparable_length == 0:
            return False

        similarity = (
            matching_tokens
            / comparable_length
        )

        return (
            similarity
            >= 0.70
        )

    def _group_boxes_by_page(
        self,
        boxes: list[OcrTextBox],
    ) -> dict[
        int,
        list[OcrTextBox],
    ]:
        grouped: dict[
            int,
            list[OcrTextBox],
        ] = {}

        for box in boxes:
            grouped.setdefault(
                box.page_number,
                [],
            ).append(
                box
            )

        return grouped

    def _ordered_page_numbers(
        self,
        *,
        boxes_by_page: dict[
            int,
            list[OcrTextBox],
        ],
        preferred_page: int | None,
    ) -> list[int]:
        page_numbers = sorted(
            boxes_by_page
        )

        if (
            preferred_page is None
            or preferred_page
            not in boxes_by_page
        ):
            return page_numbers

        return [
            preferred_page,
            *[
                page_number
                for page_number
                in page_numbers
                if page_number
                != preferred_page
            ],
        ]

    def _group_boxes_by_visual_line(
        self,
        boxes: list[OcrTextBox],
    ) -> list[
        list[OcrTextBox]
    ]:
        ordered_boxes = sorted(
            boxes,
            key=lambda box: (
                box.top,
                box.left,
            ),
        )

        visual_lines: list[
            list[OcrTextBox]
        ] = []

        for box in ordered_boxes:
            matched_line = None

            for visual_line in (
                visual_lines
            ):
                reference_top = (
                    self._average_top(
                        visual_line
                    )
                )

                if (
                    abs(
                        box.top
                        - reference_top
                    )
                    <= self.LINE_VERTICAL_TOLERANCE
                ):
                    matched_line = (
                        visual_line
                    )
                    break

            if matched_line is None:
                visual_lines.append(
                    [
                        box
                    ]
                )
            else:
                matched_line.append(
                    box
                )

        for visual_line in (
            visual_lines
        ):
            visual_line.sort(
                key=lambda box: (
                    box.left
                )
            )

        return visual_lines

    @staticmethod
    def _average_top(
        boxes: list[OcrTextBox],
    ) -> float:
        return (
            sum(
                box.top
                for box in boxes
            )
            / len(
                boxes
            )
        )

    # ------------------------------------------------------------------
    # RENDERIZAÇÃO
    # ------------------------------------------------------------------

    def _render_annotated_page(
        self,
        *,
        pdf_path: str,
        page_number: int,
        evidence_index: int,
        left: int | float,
        top: int | float,
        width: int | float,
        height: int | float,
        output_dir: Path,
    ) -> tuple[
        Path,
        Path,
    ]:
        """
        Renderiza a página com Matrix(2, 2).

        Para OCR, as coordenadas já estão nesta escala.
        Para texto nativo, o chamador converte previamente a região para
        a escala renderizada, mantendo o PromptInjectionLocation em
        coordenadas documentais originais.
        """

        render_matrix = (
            pymupdf.Matrix(
                2,
                2,
            )
        )

        with pymupdf.open(
            pdf_path
        ) as document:
            page = (
                document.load_page(
                    page_number - 1
                )
            )

            pixmap = (
                page.get_pixmap(
                    matrix=render_matrix,
                    alpha=False,
                )
            )

            image = (
                Image.frombytes(
                    "RGB",
                    (
                        pixmap.width,
                        pixmap.height,
                    ),
                    pixmap.samples,
                )
            )

        source_image_path = (
            output_dir
            / (
                f"page_"
                f"{page_number}_source.png"
            )
        )

        annotated_image_path = (
            output_dir
            / (
                f"page_"
                f"{page_number}_"
                f"prompt_injection_"
                f"{evidence_index}_"
                f"annotated.png"
            )
        )

        image.save(
            source_image_path
        )

        annotated_image = (
            image.copy()
        )

        draw = ImageDraw.Draw(
            annotated_image
        )

        # Região de fonte sub-1pt pode ter altura de poucos pixels.
        # Um padding maior torna a evidência revisável sem alterar o bbox
        # objetivo armazenado em PromptInjectionLocation.
        padding = 16

        x1 = max(
            float(left)
            - padding,
            0.0,
        )

        y1 = max(
            float(top)
            - padding,
            0.0,
        )

        x2 = min(
            float(left)
            + float(width)
            + padding,
            float(
                annotated_image.width
            ),
        )

        y2 = min(
            float(top)
            + float(height)
            + padding,
            float(
                annotated_image.height
            ),
        )

        draw.rectangle(
            (
                x1,
                y1,
                x2,
                y2,
            ),
            outline="red",
            width=6,
        )

        annotated_image.save(
            annotated_image_path
        )

        return (
            source_image_path,
            annotated_image_path,
        )

    # ------------------------------------------------------------------
    # NORMALIZAÇÃO / RESULTADO NEGATIVO
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            return ""

        decomposed = (
            unicodedata.normalize(
                "NFKD",
                value,
            )
        )

        without_accents = "".join(
            character
            for character
            in decomposed
            if not unicodedata.combining(
                character
            )
        )

        lowered = (
            without_accents.casefold()
        )

        cleaned = re.sub(
            r"[^a-z0-9]+",
            " ",
            lowered,
        )

        return (
            " ".join(
                cleaned.split()
            )
        )

    def _not_located(
        self,
        *,
        evidence: PromptInjectionEvidence,
        evidence_index: int,
        message: str,
    ) -> PromptInjectionLocation:
        return PromptInjectionLocation(
            evidence_index=evidence_index,
            evidence_code=evidence.code,
            detector=evidence.detector,
            page_number=evidence.page_number,
            matched_content=None,
            left=None,
            top=None,
            width=None,
            height=None,
            confidence=None,
            source_image_path=None,
            annotated_image_path=None,
            located=False,
            message=message,
            source=None,
            font_name=None,
            font_size=None,
            font_color_hex=None,
            is_tiny_text=None,
            is_white_text=None,
        )