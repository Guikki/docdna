import re
from dataclasses import replace
from collections import defaultdict
from math import isfinite

from app.domain.models.ocr_text_box import OcrTextBox

from app.domain.models.document_ocr import DocumentOcr
from app.domain.models.document_text import DocumentText
from app.domain.models.printed_numeric_line import PrintedNumericLine
from app.domain.services.document_identifier_service import DocumentIdentifierService
from app.domain.services.numeric_line_visual_evidence_builder import NumericLineVisualEvidenceBuilder


class PrintedNumericLineReader:

    MIN_DIGITS = 40
    MAX_DIGITS = 50

    def read(
        self,
        native_text: DocumentText,
        ocr: DocumentOcr,
        *,
        ocr_text_boxes: list[OcrTextBox] | None = None,
        identifier_observations: list[dict] | None = None,
        normalized_document=None,
    ) -> list[PrintedNumericLine]:
        """
        Extrai todas as ocorrências de possíveis linhas numéricas.

        Ocorrências repetidas são preservadas propositalmente.

        Duas sequências com o mesmo conteúdo normalizado podem representar
        observações diferentes, por exemplo:

        - duas aparições distintas no mesmo documento;
        - uma ocorrência em texto nativo e outra obtida por OCR;
        - repetições em regiões ou páginas diferentes.

        A deduplicação, quando necessária, deve ocorrer posteriormente por
        meio dos índices e regras analíticas, sem destruir a ocorrência
        original.
        """
        detected_lines: list[
            PrintedNumericLine
        ] = []

        sources = [
            (
                "native_text",
                native_text.content,
            ),
            (
                "ocr",
                ocr.content,
            ),
        ]

        for (
            source_name,
            content,
        ) in sources:
            candidates = (
                self._extract_candidates(
                    content
                )
            )

            for (
                raw_content,
                normalized_content,
            ) in candidates:
                detected_lines.append(
                    PrintedNumericLine(
                        line_index=(
                            len(
                                detected_lines
                            )
                            + 1
                        ),
                        source=source_name,
                        raw_content=(
                            raw_content
                        ),
                        normalized_content=(
                            normalized_content
                        ),
                        digit_count=len(
                            normalized_content
                        ),
                    )
                )

        # Complementa apenas sequências ausentes do OCR agregado. Não corrige
        # dígitos nem promove o candidato a linha válida. A localização será
        # confirmada pelo builder visual usando estas mesmas caixas.
        existing_ocr = {
            line.normalized_content for line in detected_lines if line.source == "ocr"
        }
        for raw, digits in self._collection_candidates_from_boxes(ocr_text_boxes or []):
            if digits not in existing_ocr:
                detected_lines.append(PrintedNumericLine(
                    line_index=len(detected_lines) + 1,
                    source="ocr", raw_content=raw,
                    normalized_content=digits, digit_count=len(digits),
                ))
        observations = identifier_observations
        if observations is None:
            observations = DocumentIdentifierService().extract(ocr_text_boxes=ocr_text_boxes or [])
        native_boxes = DocumentIdentifierService._native_boxes(normalized_document)
        return [self._classify_field_concatenation(
                    line, observations, native_boxes if line.source == "native_text" else ocr_text_boxes or [],
                )
                for line in detected_lines]

    @staticmethod
    def _classify_field_concatenation(line: PrintedNumericLine, observations: list[dict], boxes):
        # A quantidade de dígitos nunca decide a natureza da observação.
        tokens = [re.sub(r"\D", "", token) for token in line.raw_content.split()]
        tokens = [token for token in tokens if token]
        if len(tokens) < 2 or "".join(tokens) != line.normalized_content:
            return line
        if line.source not in {"ocr", "native_text"} or not boxes:
            return line
        locator = NumericLineVisualEvidenceBuilder()
        occurrences = []
        for page, page_boxes in locator._group_boxes_by_page(boxes).items():
            for row in locator._group_boxes_by_visual_line(page_boxes):
                for matched_boxes, _ in locator._find_all_matches_in_visual_line(
                    line.normalized_content, row,
                ):
                    occurrences.append((page, matched_boxes))
        if len(occurrences) != 1:
            return line
        origin_page, origin_boxes = occurrences[0]
        origin = (min(b.left for b in origin_boxes), min(b.top for b in origin_boxes),
                  max(b.left + b.width for b in origin_boxes),
                  max(b.top + b.height for b in origin_boxes))
        grouped = defaultdict(list)
        for item in observations:
            if item.get("reading_conflict"):
                continue
            if (item.get("kind") not in {"account", "customer", "invoice", "automatic_debit"}
                    or type(item.get("page_number")) is not int
                    or not item.get("value_region")):
                continue
            if item.get("source") != "NATIVE_SPAN":
                confidence = item.get("confidence")
                # Mesmo piso conservador de 80% usado no contexto financeiro;
                # OCR incerto não autoriza excluir uma candidata de pagamento.
                if not isinstance(confidence, (int, float)) or not isfinite(confidence) or confidence < 80:
                    continue
            grouped[(item["page_number"], item.get("source"), item.get("coordinate_system"))].append(item)
        supports = []
        for (page, source, units), fields in grouped.items():
            if page != origin_page or units not in {"ocr_pixels", "pdf_points"}:
                continue
            matched = []
            for token in tokens:
                choices = [f for f in fields if f.get("value") == token]
                if len(choices) == 1:
                    matched.append(choices[0])
            if len({f["kind"] for f in matched}) < 2:
                continue
            regions = [f["value_region"] for f in matched]
            if any(not all(isfinite(r[k]) for k in ("left", "top", "width", "height"))
                   or r["width"] <= 0 or r["height"] <= 0 for r in regions):
                continue
            scale = 2 if units == "pdf_points" else 1
            if any(not (origin[0] <= scale * (r["left"] + r["width"] / 2) <= origin[2]
                        and origin[1] <= scale * (r["top"] + r["height"] / 2) <= origin[3])
                   for r in regions):
                continue
            # Células distintas, na ordem textual e na mesma linha visual.
            if any(a["left"] + a["width"] > b["left"]
                   or abs(a["top"] - b["top"]) > min(a["height"], b["height"]) * .5
                   for a, b in zip(regions, regions[1:])):
                continue
            supports.append({"page_number": page, "source": source,
                             "coordinate_system": units, "fields": matched,
                             "reason": "Sequência formada por células rotuladas distintas; "
                                       "observação preservada, sem tipificação como linha de pagamento."})
        if len(supports) != 1:
            return line
        return replace(line, contextual_kind="concatenated_fields", contextual_metadata=supports[0])

    @staticmethod
    def _collection_candidates_from_boxes(boxes: list[OcrTextBox]):
        """Recupera quatro blocos de 12 dígitos na mesma região horizontal.

        Não une páginas, linhas, colunas afastadas ou tokens separados por
        palavras. A segmentação textual do Tesseract pode dividir uma linha
        visual em blocos diferentes. As caixas originais permanecem intactas.
        """
        rows: list[list[OcrTextBox]] = []
        eligible = [box for box in boxes if (
            type(box.page_number) is int and box.page_number > 0
            and all(isfinite(v) for v in (box.left, box.top, box.width, box.height))
            and box.width > 0 and box.height > 0
        )]
        for box in sorted(eligible, key=lambda b: (b.page_number, b.top, b.left)):
            if (rows and rows[-1][0].page_number == box.page_number
                    and abs(rows[-1][0].top - box.top)
                    <= min(rows[-1][0].height, box.height) * 0.5):
                rows[-1].append(box)
            else:
                rows.append([box])
        for row in rows:
            run: list[OcrTextBox] = []
            for box in sorted(row, key=lambda b: b.left):
                numeric = re.fullmatch(r"[0-9]{12}", box.text.strip()) is not None
                close = not run or (
                    0 <= box.left - (run[-1].left + run[-1].width)
                    <= 6 * min(box.height, run[-1].height)
                )
                if not numeric or not close:
                    if len(run) == 4:
                        raw = " ".join(b.text.strip() for b in run)
                        yield raw, raw.replace(" ", "")
                    run = []
                if numeric:
                    run.append(box)
            if len(run) == 4:
                raw = " ".join(b.text.strip() for b in run)
                yield raw, raw.replace(" ", "")

    def _extract_candidates(
        self,
        content: str,
    ) -> list[
        tuple[str, str]
    ]:
        if not content:
            return []

        # Limites obrigatórios impedem fatiar fluxos longos de dígitos
        # em pseudo-linhas de 40-50 posições.
        #
        # Separadores HORIZONTAIS são permitidos entre os dígitos;
        # quebras de linha não são consumidas. Dois pagamentos em
        # linhas consecutivas devem permanecer duas ocorrências.
        # Não une trechos de linhas visualmente distintas, o que
        # exigiria associação contextual e evidência de posição.
        pattern = re.compile(
            r"(?<!\d)(?:\d[ \t.\-]*){40,50}(?!\d)"
        )

        candidates: list[
            tuple[str, str]
        ] = []

        for match in pattern.finditer(
            content
        ):
            raw_content = (
                match.group()
                .strip()
            )

            normalized_content = (
                re.sub(
                    r"\D",
                    "",
                    raw_content,
                )
            )

            if not (
                self.MIN_DIGITS
                <= len(
                    normalized_content
                )
                <= self.MAX_DIGITS
            ):
                continue

            candidates.append(
                (
                    raw_content,
                    normalized_content,
                )
            )

        return candidates
