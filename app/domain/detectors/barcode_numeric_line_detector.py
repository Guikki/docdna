from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from math import isfinite

from app.domain.detectors.base_detector import BaseDetector
from app.domain.evidence.evidence import Evidence, EvidenceSeverity
from app.domain.models.analysis_context import AnalysisContext
from app.domain.models.barcode_line_comparison import (
    BarcodeLineComparison,
    BarcodeLineComparisonStatus,
)
from app.domain.models.numeric_line_validation import (
    NumericLineValidationStatus,
)
from app.domain.rules.numeric_line_converter import NumericLineConverter
from app.domain.services.native_numeric_line_corrobator import (
    NativeNumericLineCorroborator,
)


class BarcodeNumericLineDetector(BaseDetector):
    """Compara linhas validadas com códigos de pagamento da mesma página.

    A comparação é conservadora: uma coincidência de conteúdo em páginas
    diferentes não autoriza MATCH, e uma diferença não autoriza MISMATCH
    quando a linha não está localizada ou a associação é ambígua.
    """

    # A classificação contextual é independente da comparação com ITF.
    # Limiares usam coordenadas da renderização OCR (Matrix(2, 2)).
    _MIN_LOCATION_CONFIDENCE = 0.80
    _MIN_LABEL_CONFIDENCE = 0.80
    _MAX_LABEL_HORIZONTAL_GAP = 100
    _MAX_LABEL_VERTICAL_GAP = 75
    _MAX_LABEL_TOKEN_GAP = 55
    _MAX_LABEL_TOKEN_CENTER_DELTA = 24

    # Rótulos intencionalmente específicos: "conta", "fatura" e "valor"
    # não identificam por si só uma linha digitável para pagamento.
    _PAYMENT_LABEL = re.compile(
        r"\blinha\s+(?:digitavel|para\s+(?:o\s+)?pagamento|"
        r"de\s+pagamento)\b|\bcodigo\s+digitavel\b"
    )

    _ITF_FORMATS = frozenset({
        "ITF",
        "INTERLEAVED2OF5",
        "I2OF5",
    })

    def classify_candidates(self, context: AnalysisContext) -> list:
        """Descreve suporte contextual; não modifica VALID/INVALID/MISMATCH."""
        validations = {v.line_index: v for v in context.numeric_line_validations}
        result = []
        for line in context.printed_numeric_lines:
            if getattr(line, "contextual_kind", None) == "concatenated_fields":
                result.append(line)
                continue
            validation = validations.get(line.line_index)
            observed_location = next((loc for loc in context.numeric_line_locations
                                      if loc.line_index == line.line_index), None)
            trusted = self._unique_trusted_location(context, validation) if validation else None
            supported = False
            if trusted is not None:
                supported = (
                    validation.status == NumericLineValidationStatus.VALID
                    or self._nearby_payment_label_confidence(context=context, location=trusted) is not None
                    or self._nearby_itf_geometry_confidence(
                        context=context, location=trusted, validation=validation,
                    ) is not None
                )
            result.append(replace(
                line,
                contextual_kind="payment_line_candidate" if supported else "unresolved_numeric_sequence",
                contextual_metadata={
                    "reason": ("Formato/contexto de pagamento e localização confiável; vínculo não confirmado."
                               if supported else "Suporte contextual ou confiança insuficientes; observação inconclusiva."),
                    "page_number": getattr(observed_location, "page_number", None),
                    "confidence_ocr_percent": getattr(observed_location, "confidence", None),
                    "bounds_ocr_pixels": self._valid_rectangle(observed_location)
                    if observed_location is not None else None,
                    "source": line.source,
                    "association_status": "CONTEXTUAL_NOT_PROVEN" if supported else "UNRESOLVED",
                },
            ))
        return result

    def analyze(self, context: AnalysisContext) -> list[Evidence]:
        comparisons = self.compare(context)
        evidences: list[Evidence] = []

        for comparison in comparisons:
            if comparison.status == BarcodeLineComparisonStatus.MATCH:
                evidences.append(
                    Evidence(
                        code="BARCODE_LINE_MATCH",
                        title=(
                            "Código de barras e linha digitável "
                            "correspondentes"
                        ),
                        description=comparison.message,
                        severity=EvidenceSeverity.INFO,
                        detector=self.__class__.__name__,
                        confidence=1.0,
                    )
                )

            elif comparison.status == BarcodeLineComparisonStatus.MISMATCH:
                evidences.append(
                    Evidence(
                        code="BARCODE_LINE_MISMATCH",
                        title=(
                            "Divergência entre código de barras "
                            "e linha digitável"
                        ),
                        description=comparison.message,
                        severity=EvidenceSeverity.HIGH,
                        detector=self.__class__.__name__,
                        confidence=1.0,
                    )
                )

        # Linhas com estrutura inválida possuem um achado próprio.
        # A comparação linha × ITF continua inconclusiva nesses casos.
        evidences.extend(self._contextual_invalid_line_evidences(context))
        return evidences

    def compare(
        self,
        context: AnalysisContext,
    ) -> list[BarcodeLineComparison]:
        converter = NumericLineConverter()
        comparisons: list[BarcodeLineComparison] = []

        for validation in context.numeric_line_validations:
            if validation.status != NumericLineValidationStatus.VALID:
                comparisons.append(
                    self._inconclusive(
                        validation=validation,
                        converted_barcode=None,
                        message=(
                            "A sequência numérica não pôde ser comparada "
                            "porque não foi validada estruturalmente."
                        ),
                    )
                )
                continue

            converted_barcode = converter.convert_to_barcode(validation)
            if not converted_barcode:
                comparisons.append(
                    self._inconclusive(
                        validation=validation,
                        converted_barcode=None,
                        message=(
                            "A linha digitável foi validada, mas não "
                            "pôde ser convertida em código de pagamento."
                        ),
                    )
                )
                continue

            page_number = self._line_page_number(
                context=context,
                line_index=validation.line_index,
            )
            if page_number is None:
                comparisons.append(
                    self._inconclusive(
                        validation=validation,
                        converted_barcode=converted_barcode,
                        message=(
                            "Não foi possível localizar a página da linha "
                            "digitável com segurança. A comparação com "
                            "códigos de outras páginas não é conclusiva."
                        ),
                    )
                )
                continue

            candidates = self._payment_barcodes_on_page(
                context=context,
                page_number=page_number,
            )
            if not candidates:
                comparisons.append(
                    self._inconclusive(
                        validation=validation,
                        converted_barcode=converted_barcode,
                        message=(
                            f"Nenhum código de barras de pagamento ITF foi "
                            f"identificado na página {page_number} da linha "
                            "digitável."
                        ),
                    )
                )
                continue

            different_contents = {
                self._normalize_digits(barcode.content)
                for barcode in candidates
            }
            if len(different_contents) > 1:
                comparisons.append(
                    self._inconclusive(
                        validation=validation,
                        converted_barcode=converted_barcode,
                        message=(
                            f"Há diferentes códigos ITF na página "
                            f"{page_number}; não é seguro escolher um "
                            "deles sem vinculação visual à linha digitável."
                        ),
                    )
                )
                continue

            # Havendo cópias do mesmo ITF na página, não há dúvida
            # sobre qual conteúdo será comparado (apenas qual região).
            selected_barcode = candidates[0]
            detected_content = self._normalize_digits(selected_barcode.content)

            if detected_content == converted_barcode:
                status = BarcodeLineComparisonStatus.MATCH
                message = (
                    f"Na página {page_number}, o conteúdo da linha "
                    "digitável corresponde ao código ITF detectado."
                )
            else:
                status = BarcodeLineComparisonStatus.MISMATCH
                message = (
                    f"Na página {page_number}, o código ITF de "
                    "pagamento detectado difere do conteúdo convertido "
                    "da linha digitável. Conferir a vinculação visual "
                    "dos elementos à mesma cobrança."
                )

            comparisons.append(
                BarcodeLineComparison(
                    line_index=validation.line_index,
                    barcode_index=selected_barcode.barcode_index,
                    line_type=validation.line_type.value,
                    printed_numeric_line=validation.normalized_content,
                    converted_barcode=converted_barcode,
                    detected_barcode=selected_barcode.content,
                    status=status,
                    message=message,
                )
            )

        return comparisons

    def _inconclusive(
        self,
        *,
        validation,
        converted_barcode: str | None,
        message: str,
    ) -> BarcodeLineComparison:
        return BarcodeLineComparison(
            line_index=validation.line_index,
            barcode_index=None,
            line_type=validation.line_type.value,
            printed_numeric_line=validation.normalized_content,
            converted_barcode=converted_barcode,
            detected_barcode=None,
            status=BarcodeLineComparisonStatus.INCONCLUSIVE,
            message=message,
        )

    def _line_page_number(
        self,
        *,
        context: AnalysisContext,
        line_index: int,
    ) -> int | None:
        """Exige localização explícita; não deduz página pela ordem do OCR."""
        matched_pages: set[int] = set()
        for location in getattr(context, "numeric_line_locations", []) or []:
            if getattr(location, "line_index", None) != line_index:
                continue
            if getattr(location, "located", False) is not True:
                continue

            page_number = getattr(location, "page_number", None)
            if (
                isinstance(page_number, int)
                and not isinstance(page_number, bool)
                and page_number > 0
            ):
                matched_pages.add(page_number)

        # Se as localizações forem conflitantes, não há vínculo seguro.
        if len(matched_pages) != 1:
            return None
        return next(iter(matched_pages))

    def _payment_barcodes_on_page(
        self,
        *,
        context: AnalysisContext,
        page_number: int,
    ) -> list:
        return [
            barcode
            for barcode in context.barcodes
            if getattr(barcode, "page_number", None) == page_number
            and self._is_payment_barcode(
                content=getattr(barcode, "content", ""),
                barcode_format=getattr(barcode, "format", None),
            )
        ]

    def _find_compatible_barcode(
        self,
        converted_barcode: str | None,
        context: AnalysisContext,
        page_number: int | None = None,
    ):
        """Busca apenas ITF na página conhecida (compatibilidade interna)."""
        if not converted_barcode or page_number is None:
            return None
        for barcode in self._payment_barcodes_on_page(
            context=context,
            page_number=page_number,
        ):
            if self._normalize_digits(barcode.content) == converted_barcode:
                return barcode
        return None

    def _is_payment_barcode(
        self,
        content: str,
        barcode_format: str | None = None,
    ) -> bool:
        """Reconhece apenas códigos ITF com 44 dígitos decodificados."""
        format_name = str(barcode_format or "").strip().upper()
        format_name = format_name.rsplit(".", 1)[-1]
        format_name = "".join(
            char for char in format_name if char.isalnum()
        )
        if format_name not in self._ITF_FORMATS:
            return False

        normalized_content = self._normalize_digits(content)
        return len(normalized_content) == 44

    def _normalize_digits(self, content: str) -> str:
        return "".join(
            character
            for character in content
            if character.isdigit()
        )

    def _contextual_invalid_line_evidences(
        self,
        context: AnalysisContext,
    ) -> list[Evidence]:
        """Não converte números isolados em evidências de pagamento.

        Só emite uma evidência quando há simultaneamente anomalia
        estrutural objetiva, localização inequívoca (OCR confiável ou
        texto nativo corroborado espacialmente) e contexto financeiro
        por rótulo ou ITF próximo.
        """
        evidences: list[Evidence] = []
        for validation in getattr(context, "numeric_line_validations", []) or []:
            if any(getattr(line, "line_index", None) == validation.line_index
                   and getattr(line, "contextual_kind", None) == "concatenated_fields"
                   for line in getattr(context, "printed_numeric_lines", []) or []):
                continue
            reason = self._structural_invalidity_reason(validation)
            if reason is None:
                continue

            location = self._unique_trusted_location(context, validation)
            if location is None:
                continue

            label_confidence = self._nearby_payment_label_confidence(
                context=context,
                location=location,
            )
            context_method = "rotulo financeiro proximo"
            # Uma fatura pode trazer a linha logo acima do codigo ITF,
            # sem qualquer rotulo OCR. A geometria e uma via de prova
            # ALTERNATIVA, nunca uma suposicao pela mera pagina comum.
            if label_confidence is None:
                label_confidence = self._nearby_itf_geometry_confidence(
                    context=context,
                    location=location,
                    validation=validation,
                )
                context_method = "proximidade espacial com codigo ITF"
            if label_confidence is None:
                continue

            page = location.page_number
            line_index = validation.line_index
            ocr_confidence = self._normalize_confidence(location.confidence)
            # Uma corroboração nativa é uma fonte adicional de proveniência,
            # nunca uma alteração retroativa da confiança OCR registrada.
            native_corroborated = (
                ocr_confidence < self._MIN_LOCATION_CONFIDENCE
                and self._native_line_corroborated(context, validation, location)
            )
            location_support = 0.85 if native_corroborated else ocr_confidence
            confidence = min(location_support, label_confidence)
            source_note = (
                " A camada de texto nativo do PDF confirmou integralmente "
                "a sequência na mesma região; a confiança OCR original "
                f"permaneceu em {location.confidence}/100."
                if native_corroborated else ""
            )
            evidences.append(
                Evidence(
                    code="PAYMENT_LINE_INVALID_STRUCTURE",
                    title="Linha digitável de pagamento com estrutura inválida",
                    description=(
                        f"Na página {page}, a sequência numérica "
                        f"(índice da linha {line_index}) foi localizada "
                        f"no contexto de {context_method}. "
                        f"{reason}{source_note} "
                        "A identificação contextual recomenda conferência "
                        "do documento original; não comprova fraude nem "
                        "estabelece divergência com um ITF específico."
                    ),
                    severity=EvidenceSeverity.MEDIUM,
                    detector=self.__class__.__name__,
                    confidence=round(confidence, 4),
                )
            )
        return evidences

    def _structural_invalidity_reason(self, validation) -> str | None:
        content = str(getattr(validation, "normalized_content", "") or "")
        # Apenas dígitos ASCII exatos. Uma aproximação do OCR não autoriza
        # afirmar invalidez sem informação estrutural suficiente.
        if not content.isascii() or not content.isdigit():
            return None
        if len(content) not in (47, 48):
            return None

        status = getattr(validation, "status", None)
        if status == NumericLineValidationStatus.VALID:
            return None

        if status == NumericLineValidationStatus.INVALID:
            # Validador já demonstrou a falha, tipicamente nos DVs.
            message = str(getattr(validation, "message", "") or "").strip()
            return message or "Falha na verificação estrutural da linha de pagamento."

        if status != NumericLineValidationStatus.INCONCLUSIVE:
            return None

        # Casos outrora inconclusivos, mas com cabeçalho estrutural
        # impossível para linha de arrecadação de 48 dígitos.
        # Sem o contexto rotulado, continuam inconclusivos.
        if len(content) == 48:
            if content[0] != "8":
                return (
                    "Uma linha de arrecadação com 48 dígitos deve iniciar "
                    "com 8; a sequência localizada possui outro início."
                )
            if content[2] not in "6789":
                return (
                    "O identificador de referência (terceiro dígito) "
                    "não é um dos indicadores reconhecidos: 6, 7, 8 ou 9."
                )
        return None

    def _unique_trusted_location(self, context: AnalysisContext, validation):
        locations = [
            loc for loc in (getattr(context, "numeric_line_locations", []) or [])
            if getattr(loc, "line_index", None) == validation.line_index
        ]
        # Não transformar múltiplas ocorrências em uma localização arbitrária.
        if len(locations) != 1:
            return None

        location = locations[0]
        if getattr(location, "located", None) is not True:
            return None
        page = getattr(location, "page_number", None)
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return None
        ocr_confidence = self._normalize_confidence(
            getattr(location, "confidence", None)
        )
        if ocr_confidence <= 0:
            return None

        content = str(getattr(validation, "normalized_content", "") or "")
        matched = str(getattr(location, "matched_content", "") or "")
        if self._normalize_digits(matched) != content:
            return None

        if self._valid_rectangle(location) is None:
            return None
        if (
            ocr_confidence < self._MIN_LOCATION_CONFIDENCE
            and not self._native_line_corroborated(context, validation, location)
        ):
            return None
        return location

    def _native_line_corroborated(self, context, validation, location) -> bool:
        """Não usa texto nativo genérico: exige confirmação espacial única."""
        return NativeNumericLineCorroborator().confirms(
            pdf_path=str(getattr(context, "saved_path", "") or ""),
            page_number=getattr(location, "page_number", None),
            expected_digits=str(getattr(validation, "normalized_content", "") or ""),
            ocr_left=getattr(location, "left", None),
            ocr_top=getattr(location, "top", None),
            ocr_width=getattr(location, "width", None),
            ocr_height=getattr(location, "height", None),
        )

    def _nearby_payment_label_confidence(
        self,
        *,
        context: AnalysisContext,
        location,
    ) -> float | None:
        rect = self._valid_rectangle(location)
        if rect is None:
            return None
        left, top, right, bottom = rect

        # Filtro espacial antes da combinação das palavras.
        nearby = []
        for box in getattr(context, "ocr_text_boxes", []) or []:
            if getattr(box, "page_number", None) != location.page_number:
                continue
            confidence = self._normalize_confidence(
                getattr(box, "confidence", None)
            )
            if confidence < self._MIN_LABEL_CONFIDENCE:
                continue
            box_rect = self._valid_rectangle(box)
            if box_rect is None:
                continue
            bx1, by1, bx2, by2 = box_rect
            if (
                bx2 < left - 500
                or bx1 > right + self._MAX_LABEL_HORIZONTAL_GAP
                or by2 < top - 125
                or by1 > bottom + self._MAX_LABEL_VERTICAL_GAP
            ):
                continue
            nearby.append((box, box_rect, confidence))

        # O Tesseract fornece tipicamente uma caixa por palavra; por isso
        # reconstruímos rótulos curtos na mesma linha física, sem unir
        # palavras distantes ou de linhas diferentes.
        nearby.sort(key=lambda item: (item[1][0], item[1][1]))
        best_confidence: float | None = None
        for index, (first_box, first_rect, first_conf) in enumerate(nearby):
            fragments: list[str] = []
            current_rect = first_rect
            min_confidence = first_conf
            previous_rect = None
            first_center_y = (first_rect[1] + first_rect[3]) / 2

            for box, box_rect, confidence in nearby[index:index + 5]:
                if previous_rect is not None:
                    center_y = (box_rect[1] + box_rect[3]) / 2
                    horizontal_gap = box_rect[0] - previous_rect[2]
                    if (
                        abs(center_y - first_center_y)
                        > self._MAX_LABEL_TOKEN_CENTER_DELTA
                        or horizontal_gap > self._MAX_LABEL_TOKEN_GAP
                        or horizontal_gap < -10
                    ):
                        break
                    current_rect = (
                        min(current_rect[0], box_rect[0]),
                        min(current_rect[1], box_rect[1]),
                        max(current_rect[2], box_rect[2]),
                        max(current_rect[3], box_rect[3]),
                    )
                fragments.append(str(getattr(box, "text", "") or ""))
                min_confidence = min(min_confidence, confidence)
                previous_rect = box_rect
                label = self._fold_label(" ".join(fragments))
                if not self._PAYMENT_LABEL.search(label):
                    continue
                if not self._rectangles_near(current_rect, rect):
                    continue
                best_confidence = max(best_confidence or 0.0, min_confidence)
        return best_confidence

    def _nearby_itf_geometry_confidence(
        self, *, context: AnalysisContext, location, validation
    ) -> float | None:
        """Via alternativa de evidência para linhas de arrecadação.

        Exige ITF real, com retângulo próprio, espacialmente próximo
        da sequência OCR. A mesma página SEM geometria NÃO basta.
        Não infere que os dois meios sejam necessariamente da mesma cobrança.
        """
        content = str(getattr(validation, "normalized_content", "") or "")
        if len(content) != 48:
            return None
        line_rect = self._valid_rectangle(location)
        if line_rect is None:
            return None

        nearby = []
        for barcode in self._payment_barcodes_on_page(
            context=context, page_number=location.page_number
        ):
            # Exigir localização do ZXing; pagina isolada é insuficiente.
            loc = getattr(barcode, "location", None)
            if loc is None or getattr(loc, "page_number", None) != location.page_number:
                continue
            box = getattr(loc, "bounding_box", None)
            if box is None:
                continue
            try:
                # BoundingBox usa pontos de PDF; OCR usa Matrix(2, 2).
                x = float(box.x) * 2
                y = float(box.y) * 2
                w = float(box.width) * 2
                h = float(box.height) * 2
            except (AttributeError, ValueError, TypeError):
                continue
            if (
                not all(isfinite(n) for n in (x, y, w, h))
                or x < 0 or y < 0 or w <= 0 or h <= 0
            ):
                continue
            itf_rect = (x, y, x + w, y + h)
            a1, b1, a2, b2 = line_rect
            c1, d1, c2, d2 = itf_rect
            horizontal_overlap = max(0.0, min(a2, c2) - max(a1, c1))
            min_width = min(a2 - a1, c2 - c1)
            vertical_gap = max(0.0, d1 - b2, b1 - d2)
            if min_width <= 0 or horizontal_overlap / min_width < 0.35:
                continue
            if vertical_gap > 160:
                continue
            nearby.append(barcode)

        # Se houver múltiplos códigos próximos, só há contexto suficiente
        # se for exatamente o MESMO ITF (repetição visual idêntica).
        distinct_itfs = {
            self._normalize_digits(b.content) for b in nearby
        }
        if len(distinct_itfs) != 1:
            return None
        # Confiança contextual limitada: geometria não prova a vinculação.
        return 0.85

    def _fold_label(self, value: str) -> str:
        value = unicodedata.normalize("NFKD", value)
        value = "".join(char for char in value if not unicodedata.combining(char))
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    def _normalize_confidence(self, value) -> float:
        """Aceita confiança normalizada (0-1) ou do Tesseract (0-100)."""
        if isinstance(value, bool):
            return -1.0
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return -1.0
        if not isfinite(parsed) or parsed < 0 or parsed > 100:
            return -1.0
        return parsed / 100 if parsed > 1 else parsed

    def _valid_rectangle(self, obj) -> tuple[float, float, float, float] | None:
        try:
            x = float(getattr(obj, "left"))
            y = float(getattr(obj, "top"))
            w = float(getattr(obj, "width"))
            h = float(getattr(obj, "height"))
        except (TypeError, ValueError, AttributeError):
            return None
        if (
            not all(isfinite(v) for v in (x, y, w, h))
            or x < 0 or y < 0 or w <= 0 or h <= 0
        ):
            return None
        return x, y, x + w, y + h

    def _rectangles_near(
        self,
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        ax1, ay1, ax2, ay2 = first
        bx1, by1, bx2, by2 = second
        horizontal_gap = max(0.0, bx1 - ax2, ax1 - bx2)
        vertical_gap = max(0.0, by1 - ay2, ay1 - by2)
        return (
            horizontal_gap <= self._MAX_LABEL_HORIZONTAL_GAP
            and vertical_gap <= self._MAX_LABEL_VERTICAL_GAP
        )
