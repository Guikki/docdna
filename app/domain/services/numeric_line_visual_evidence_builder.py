from pathlib import Path
from re import sub

import pymupdf
from PIL import Image, ImageDraw

from app.config.settings import settings
from app.domain.models.numeric_line_location import NumericLineLocation
from app.domain.models.ocr_text_box import OcrTextBox
from app.domain.models.printed_numeric_line import PrintedNumericLine


class NumericLineVisualEvidenceBuilder:

    BANK_LINE_LENGTH = 47
    COLLECTION_LINE_LENGTH = 48
    LINE_VERTICAL_TOLERANCE = 20

    def build(
        self,
        pdf_path: str,
        lines: list[PrintedNumericLine],
        boxes: list[OcrTextBox],
    ) -> list[NumericLineLocation]:
        source_path = Path(pdf_path)

        output_dir = (
            settings.EXTRACTED_DIR
            / source_path.stem
            / "numeric-line-evidence"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        return [
            self._locate_line(
                pdf_path=pdf_path,
                line=line,
                boxes=boxes,
                output_dir=output_dir,
            )
            for line in lines
        ]

    def _locate_line(
        self,
        pdf_path: str,
        line: PrintedNumericLine,
        boxes: list[OcrTextBox],
        output_dir: Path,
    ) -> NumericLineLocation:
        """Só atribui página/coordenadas quando a localização é inequívoca.

        Uma mesma sequência pode aparecer no canhoto, no corpo da fatura,
        em mais de uma página, ou como trecho de um candidato OCR maior.
        Encontrar a primeira ocorrência não demonstra sua proveniência.
        """
        raw_target = self._normalize_digits(line.normalized_content)

        if not raw_target:
            return self._not_located(
                line_index=line.line_index,
                message=(
                    "A sequência não possui conteúdo numérico suficiente "
                    "para localização visual."
                ),
            )

        candidate_targets = self._build_candidate_targets(raw_target)
        boxes_by_page = self._group_boxes_by_page(boxes)

        # Agrupamento é independente do candidato (e evita reprocessá-lo
        # para cada subsequência de 47/48 dígitos).
        visual_lines_by_page = {
            page_number: self._group_boxes_by_visual_line(page_boxes)
            for page_number, page_boxes in boxes_by_page.items()
        }

        # Uma evidência física pode coincidir com o candidato inteiro e
        # com uma subsequência dele. Essas buscas não são ocorrências
        # distintas quando ocupam a mesma caixa delimitadora.
        locations: dict[tuple, tuple] = {}

        for target in candidate_targets:
            # Duas ocorrências DO MESMO candidato em uma única caixa OCR
            # não são desambiguadas por coordenadas: conservadoramente,
            # a posição permanece desconhecida.
            seen_for_target: set[tuple] = set()
            for page_number, visual_lines in visual_lines_by_page.items():
                for visual_line_boxes in visual_lines:
                    matches = self._find_all_matches_in_visual_line(
                        target=target,
                        visual_line_boxes=visual_line_boxes,
                        max_matches=2,
                    )
                    for matched_boxes, matched_content in matches:
                        left = min(box.left for box in matched_boxes)
                        top = min(box.top for box in matched_boxes)
                        right = max(
                            box.left + box.width for box in matched_boxes
                        )
                        bottom = max(
                            box.top + box.height for box in matched_boxes
                        )
                        location_key = (
                            page_number, left, top, right, bottom,
                        )

                        if location_key in seen_for_target:
                            return self._not_located(
                                line_index=line.line_index,
                                message=(
                                    "Localização ambígua: a mesma sequência "
                                    "aparece mais de uma vez na região "
                                    "reconhecida pelo OCR."
                                ),
                            )
                        seen_for_target.add(location_key)

                        if location_key not in locations:
                            locations[location_key] = (
                                page_number,
                                left,
                                top,
                                right - left,
                                bottom - top,
                                matched_boxes,
                                matched_content,
                                target != raw_target,
                            )

                        if len(locations) > 1:
                            return self._not_located(
                                line_index=line.line_index,
                                message=(
                                    "Localização ambígua: há correspondências "
                                    "numéricas em mais de uma página ou região "
                                    "do documento. Nenhuma posição foi "
                                    "atribuída automaticamente."
                                ),
                            )

        if not locations:
            return self._not_located(
                line_index=line.line_index,
                message=(
                    "Não foi possível confirmar visualmente a localização "
                    "da sequência numérica nem de um trecho interno "
                    "compatível com linha digitável."
                ),
            )

        (
            page_number,
            left,
            top,
            width,
            height,
            matched_boxes,
            matched_content,
            used_subsequence,
        ) = next(iter(locations.values()))

        confidence = sum(
            box.confidence for box in matched_boxes
        ) / len(matched_boxes)

        source_image_path, annotated_image_path = self._render_annotated_page(
            pdf_path=pdf_path,
            page_number=page_number,
            line_index=line.line_index,
            left=left,
            top=top,
            width=width,
            height=height,
            output_dir=output_dir,
        )

        message = (
            "Foi localizado visualmente um trecho interno compatível "
            "com linha digitável dentro da sequência capturada pelo OCR."
            if used_subsequence
            else "A sequência numérica foi localizada visualmente na página do documento."
        )

        return NumericLineLocation(
            line_index=line.line_index,
            page_number=page_number,
            matched_content=matched_content,
            left=left,
            top=top,
            width=width,
            height=height,
            confidence=confidence,
            source_image_path=str(source_image_path),
            annotated_image_path=str(annotated_image_path),
            located=True,
            message=message,
        )

    def _build_candidate_targets(
        self,
        raw_target: str,
    ) -> list[str]:
        candidates: list[str] = []

        self._append_unique(
            candidates,
            raw_target,
        )

        for expected_length in (
            self.COLLECTION_LINE_LENGTH,
            self.BANK_LINE_LENGTH,
        ):
            if len(raw_target) < expected_length:
                continue

            for start_index in range(
                len(raw_target) - expected_length + 1
            ):
                candidate = raw_target[
                    start_index:
                    start_index + expected_length
                ]

                if self._is_plausible_numeric_line(
                    candidate
                ):
                    self._append_unique(
                        candidates,
                        candidate,
                    )

        candidates.sort(
            # Localizar não é validar. Um candidato integral, mesmo com
            # estrutura desconhecida, não deve perder dígitos para uma
            # subsequência considerada mais plausível. Todas as ocorrências
            # continuam sendo examinadas para detectar ambiguidade.
            key=lambda candidate: (
                candidate != raw_target,
                self._candidate_priority(candidate),
            )
        )

        return candidates

    def _candidate_priority(
        self,
        candidate: str,
    ) -> tuple[int, int]:
        if (
            len(candidate) == self.COLLECTION_LINE_LENGTH
            and candidate.startswith("8")
        ):
            return 0, -len(candidate)

        if len(candidate) == self.BANK_LINE_LENGTH:
            return 1, -len(candidate)

        return 2, -len(candidate)

    def _is_plausible_numeric_line(
        self,
        candidate: str,
    ) -> bool:
        if (
            len(candidate) == self.COLLECTION_LINE_LENGTH
        ):
            return candidate.startswith("8")

        if len(candidate) == self.BANK_LINE_LENGTH:
            return True

        return False

    def _append_unique(
        self,
        values: list[str],
        value: str,
    ) -> None:
        if value not in values:
            values.append(value)

    def _find_match_in_visual_line(
        self,
        target: str,
        visual_line_boxes: list[OcrTextBox],
    ) -> tuple[list[OcrTextBox], str] | None:
        """Interface legada: preserva o retorno da primeira correspondência.

        A decisão sobre unicidade ocorre em _locate_line, que consome
        _find_all_matches_in_visual_line em vez deste método.
        """
        matches = self._find_all_matches_in_visual_line(
            target=target,
            visual_line_boxes=visual_line_boxes,
            max_matches=1,
        )
        return matches[0] if matches else None

    def _find_all_matches_in_visual_line(
        self,
        target: str,
        visual_line_boxes: list[OcrTextBox],
        max_matches: int = 2,
    ) -> list[tuple[list[OcrTextBox], str]]:
        """Encontra ocorrências distintas sem reutilizar caixas OCR.

        O limite de duas ocorrências basta para reconhecer ambiguidade
        e evita percorrer milhares de coincidências em texto repetitivo.
        """
        if not target or max_matches < 1:
            return []

        ordered_boxes = sorted(visual_line_boxes, key=lambda box: box.left)
        numeric_boxes = [
            (box, self._normalize_digits(box.text))
            for box in ordered_boxes
            if self._normalize_digits(box.text)
        ]
        if not numeric_boxes:
            return []

        combined_digits = "".join(digits for _, digits in numeric_boxes)
        offsets: list[tuple[int, int, OcrTextBox]] = []
        position = 0
        for box, digits in numeric_boxes:
            end = position + len(digits)
            offsets.append((position, end, box))
            position = end

        results: list[tuple[list[OcrTextBox], str]] = []
        search_start = 0
        while len(results) < max_matches:
            target_start = combined_digits.find(target, search_start)
            if target_start < 0:
                break
            target_end = target_start + len(target)
            matched_boxes = [
                box
                for box_start, box_end, box in offsets
                if box_end > target_start and box_start < target_end
            ]
            if matched_boxes:
                results.append((matched_boxes, target))
            search_start = target_start + 1
        return results

    def _trim_match_to_target(
        self,
        target: str,
        collected_boxes: list[OcrTextBox],
    ) -> tuple[list[OcrTextBox], str] | None:
        digits_by_box = [
            self._normalize_digits(box.text)
            for box in collected_boxes
        ]

        combined_digits = "".join(digits_by_box)
        target_start = combined_digits.find(target)

        if target_start < 0:
            return None

        target_end = target_start + len(target)

        matched_boxes: list[OcrTextBox] = []
        current_position = 0

        for box, digits in zip(
            collected_boxes,
            digits_by_box,
        ):
            box_start = current_position
            box_end = current_position + len(digits)

            overlaps_target = (
                box_end > target_start
                and box_start < target_end
            )

            if overlaps_target:
                matched_boxes.append(box)

            current_position = box_end

        if not matched_boxes:
            return None

        return matched_boxes, target

    def _group_boxes_by_page(
        self,
        boxes: list[OcrTextBox],
    ) -> dict[int, list[OcrTextBox]]:
        grouped: dict[int, list[OcrTextBox]] = {}

        for box in boxes:
            grouped.setdefault(
                box.page_number,
                [],
            ).append(box)

        return grouped

    def _group_boxes_by_visual_line(
        self,
        boxes: list[OcrTextBox],
    ) -> list[list[OcrTextBox]]:
        ordered_boxes = sorted(
            boxes,
            key=lambda box: (
                box.top,
                box.left,
            ),
        )

        visual_lines: list[list[OcrTextBox]] = []

        for box in ordered_boxes:
            matched_line = None

            for visual_line in visual_lines:
                reference_top = self._average_top(
                    visual_line
                )

                if (
                    abs(box.top - reference_top)
                    <= self.LINE_VERTICAL_TOLERANCE
                ):
                    matched_line = visual_line
                    break

            if matched_line is None:
                visual_lines.append([box])
            else:
                matched_line.append(box)

        for visual_line in visual_lines:
            visual_line.sort(
                key=lambda box: box.left
            )

        return visual_lines

    def _average_top(
        self,
        boxes: list[OcrTextBox],
    ) -> float:
        return sum(
            box.top
            for box in boxes
        ) / len(boxes)

    def _render_annotated_page(
            self,
            pdf_path: str,
            page_number: int,
            line_index: int,
            left: int,
            top: int,
            width: int,
            height: int,
            output_dir: Path,
    ) -> tuple[Path, Path]:
        """
        Renderiza a página usando exatamente a mesma escala
        utilizada pelo OcrReader.

        As coordenadas de OcrTextBox foram produzidas sobre uma
        imagem renderizada com Matrix(2, 2). Portanto, a evidência
        visual precisa usar a mesma matriz para que as posições
        permaneçam compatíveis.
        """
        render_matrix = pymupdf.Matrix(2, 2)

        with pymupdf.open(pdf_path) as document:
            page = document.load_page(
                page_number - 1
            )

            pixmap = page.get_pixmap(
                matrix=render_matrix,
                alpha=False,
            )

            image = Image.frombytes(
                "RGB",
                (
                    pixmap.width,
                    pixmap.height,
                ),
                pixmap.samples,
            )

        source_image_path = (
                output_dir
                / f"page_{page_number}_source.png"
        )

        annotated_image_path = (
                output_dir
                / (
                    f"page_{page_number}_"
                    f"numeric_line_{line_index}_annotated.png"
                )
        )

        image.save(source_image_path)

        annotated_image = image.copy()
        draw = ImageDraw.Draw(
            annotated_image
        )

        padding = 12

        x1 = max(
            left - padding,
            0,
        )
        y1 = max(
            top - padding,
            0,
        )
        x2 = min(
            left + width + padding,
            annotated_image.width,
        )
        y2 = min(
            top + height + padding,
            annotated_image.height,
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

    def _normalize_digits(
        self,
        content: str,
    ) -> str:
        return sub(
            r"\D",
            "",
            content,
        )

    def _not_located(
        self,
        line_index: int,
        message: str,
    ) -> NumericLineLocation:
        return NumericLineLocation(
            line_index=line_index,
            page_number=None,
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
        )
