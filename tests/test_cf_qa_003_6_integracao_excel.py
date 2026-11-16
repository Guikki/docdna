"""Reconciliação financeira conservadora e independente de documentos conhecidos.

Interpreta fatos codificados (arrecadação FEBRABAN e BR Code Pix) e
observações textuais de total a pagar. Não conclui autenticidade ou fraude.

Política de segurança:
- valor em código somente após verificação estrutural/de integridade;
- não inferir página de texto agregado de DocumentText/DocumentOcr;
- não comparar cobranças independentes só pela presença no PDF;
- REVIEW_REQUIRED = diferença para triagem, não fraude confirmada;
- não resolver URL de Pix dinâmico nem adivinhar valor ausente.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite
from typing import Iterable, Any


class FinancialReconciliationStatus(str, Enum):
    INCONCLUSIVE = "INCONCLUSIVE"
    CONSISTENT = "CONSISTENT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class FinancialValue:
    source: str
    amount: Decimal
    page_number: int | None
    barcode_index: int | None
    raw_content: str
    provenance: str
    # Coordenadas OCR em pixels da imagem, quando efetivamente observadas.
    # Não se atribuem coordenadas a texto nativo/OCR agregado.
    left: float | None = None
    top: float | None = None
    width: float | None = None
    height: float | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class FinancialComparison:
    """Comparação OBSERVACIONAL: mesma página não confirma mesma cobrança."""

    page_number: int
    sources: tuple[str, ...]
    amounts: tuple[Decimal, ...]
    relation: str  # EQUAL_VALUES | DIFFERENT_VALUES
    linkage: str = "SAME_PAGE_UNCONFIRMED"
    message: str = ""


@dataclass(frozen=True)
class FinancialReconciliationResult:
    status: FinancialReconciliationStatus
    values: list[FinancialValue]
    message: str
    issues: list[str]
    comparisons: list[FinancialComparison] = field(default_factory=list)


class FinancialReconciliationService:
    """Interpreta evidências de pagamento e sinaliza discrepâncias rastreáveis.

    Aceita objetos do domínio existentes: Barcode, DocumentText, DocumentOcr.
    O serviço não armazena estado entre chamadas nem depende de nomes ou lotes.
    """

    _ITF_FORMATS = frozenset({"itf", "interleaved2of5", "i2of5"})
    _QR_FORMATS = frozenset({"qr", "qrcode"})
    _SEGMENTS = frozenset("12345679")
    _EFFECTIVE_VALUES = frozenset("68")
    _REFERENCE_VALUES = frozenset("79")

    # Somente papéis semânticos de valor final. Deliberadamente NÃO reconhece
    # descontos, parcelas, preço de plano, tributos isolados ou montantes soltos.
    _PRINTED_TOTAL = re.compile(
        r"(?<!\w)(?:valor\s+a\s+pagar|total\s+a\s+pagar|"
        r"total\s+devido|total\s+da\s+fatura|valor\s+total\s+a\s+pagar)"
        r"\s*[:\-–—|>]*\s*(?:R\$\s*)?"
        r"(?P<amount>(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})(?!\d)",
        flags=re.IGNORECASE,
    )
    # OCR localizado: aceita valor sem R$ SOMENTE junto a rótulo inequívoco.
    _PRINTED_LABEL = re.compile(
        r"(?<!\w)(?:valor\s+a\s+pagar|total\s+a\s+pagar|"
        r"total\s+devido|total\s+da\s+fatura|"
        r"valor\s+total\s+a\s+pagar)(?!\w)", re.IGNORECASE,
    )
    _MONEY_ONLY = re.compile(
        r"^\s*(?:R\$\s*)?(?P<amount>(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})\s*$",
        re.IGNORECASE,
    )
    _PRINTED_TOTAL_LOCAL = re.compile(
        _PRINTED_LABEL.pattern +
        r"[\s:;|=>\-–—]{0,24}(?:R\$\s*)?"
        r"(?P<amount>(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})(?!\d)",
        re.IGNORECASE,
    )
    _MIN_LOCAL_CONFIDENCE_FOR_COMPARISON = 70.0

    def reconcile(
        self,
        *,
        barcodes: Iterable[Any],
        native_text: Any,
        ocr: Any,
        ocr_text_boxes: Iterable[Any] | None = None,
    ) -> FinancialReconciliationResult:
        values: list[FinancialValue] = []
        issues: list[str] = []

        for barcode in barcodes:
            content = str(getattr(barcode, "content", "") or "").strip()
            fmt = self._normalize_format(getattr(barcode, "format", ""))
            page = self._positive_int(getattr(barcode, "page_number", None))
            index = self._positive_int(getattr(barcode, "barcode_index", None))

            if fmt in self._ITF_FORMATS:
                amount, reason = self._read_collection_barcode(content)
                if amount is not None:
                    values.append(FinancialValue(
                        source="ITF", amount=amount,
                        page_number=page, barcode_index=index,
                        raw_content=content,
                        provenance="FEBRABAN_ARRECADACAO_44_DV_GERAL",
                    ))
                elif reason:
                    issues.append(self._describe_issue(reason, page, index))
            elif fmt in self._QR_FORMATS:
                amount, reason = self._read_pix_payload(content)
                if amount is not None:
                    values.append(FinancialValue(
                        source="PIX", amount=amount,
                        page_number=page, barcode_index=index,
                        raw_content=content,
                        provenance="PIX_BR_CODE_TLV_CRC16_CAMPO_54",
                    ))
                elif reason:
                    issues.append(self._describe_issue(reason, page, index))

        # Observações OCR LOCALIZADAS: mesma página e região efetivamente vistas.
        # Confiança baixa é preservada, mas não fundamenta comparação triplamente
        # correlacionada. Não inventamos posições para o texto agregado.
        localized_values = self._extract_located_printed_values(ocr_text_boxes or ())
        values.extend(localized_values)

        # DocumentText/DocumentOcr contêm texto de TODAS as páginas: não há
        # coordenada de origem para relacionar com código; page_number=None.
        # Guardamos fonte e trecho literal para investigação posterior.
        for source, document in (("native_text", native_text), ("ocr", ocr)):
            content = str(getattr(document, "content", "") or "")
            for match in self._PRINTED_TOTAL.finditer(content):
                amount = self._parse_br_money(match.group("amount"))
                if amount is None:
                    continue
                # Não duplicar OCR agregado quando o mesmo valor já foi
                # observado de forma LOCALIZADA. Texto nativo e OCR são
                # fontes independentes; a fonte nativa é mantida à parte.
                if source == "ocr" and any(
                    value.source == "PRINTED" and
                    value.provenance.startswith("OCR_TEXT_BOX") and
                    value.amount == amount
                    for value in localized_values
                ):
                    continue
                values.append(FinancialValue(
                    source="PRINTED", amount=amount,
                    page_number=None, barcode_index=None,
                    raw_content=match.group(0),
                    provenance=f"TEXT_TOTAL_LABEL:{source}",
                ))

        comparisons = self._compare_located_values(values)
        status, message = self._reconcile_evidence(values)
        # Quando há três fontes únicas na mesma página e o total OCR é
        # suficientemente confiável, diferença de valores merece TRIAGEM.
        # A situação não prova vínculo entre instrumentos nem fraude.
        three_source_difference = any(
            item.relation == "DIFFERENT_VALUES" and
            set(item.sources) == {"ITF", "PIX", "PRINTED"}
            for item in comparisons
        )
        if three_source_difference:
            status = FinancialReconciliationStatus.REVIEW_REQUIRED
            message = (
                "Diferenças observadas entre total impresso, ITF e Pix em "
                "uma mesma página. Conferir se representam a mesma cobrança; "
                "a vinculação e a autenticidade NÃO estão demonstradas."
            )
        elif comparisons and status == FinancialReconciliationStatus.INCONCLUSIVE:
            message = (
                "Há valores observados na mesma página, mas não há "
                "associação suficiente para reconciliar uma cobrança."
            )
        for comparison in comparisons:
            if comparison.relation == "DIFFERENT_VALUES":
                issues.append(comparison.message)

        return FinancialReconciliationResult(
            status=status,
            values=values,
            message=message,
            issues=issues,
            comparisons=comparisons,
        )

    @classmethod
    def _extract_located_printed_values(
        cls, boxes: Iterable[Any],
    ) -> list[FinancialValue]:
        """Localiza totais na saída REAL do Tesseract: uma caixa por palavra.

        Reconstrói linhas sem misturar páginas e aproxima rótulo/valor somente
        quando o par é único na região. O valor observado não prova que um Pix
        ou código de barras na página pertençam à mesma obrigação.
        """
        entries: dict[int, list[dict[str, Any]]] = {}
        for box in boxes:
            get = box.get if isinstance(box, dict) else lambda k, d=None: getattr(box, k, d)
            page = cls._positive_int(get("page_number"))
            text = str(get("text") or "").strip()
            coords = [get(name) for name in ("left", "top", "width", "height")]
            if not page or not text or not all(
                type(n) in (int, float) and isfinite(n) for n in coords
            ):
                continue
            left, top, width, height = (float(n) for n in coords)
            if width <= 0 or height <= 0:
                continue
            raw_conf = get("confidence")
            conf = (float(raw_conf) if type(raw_conf) in (int, float)
                    and isfinite(raw_conf) and 0 <= raw_conf <= 100 else None)
            entries.setdefault(page, []).append({
                "text": text, "left": left, "top": top,
                "width": width, "height": height, "confidence": conf,
            })

        found: list[FinancialValue] = []
        seen: set[tuple[int, Decimal, int, int]] = set()

        def append(page: int, amount_raw: str, region: list[dict[str, Any]],
                   provenance: str) -> None:
            amount = cls._parse_br_money(amount_raw)
            if amount is None:
                return
            left = min(b["left"] for b in region)
            top = min(b["top"] for b in region)
            right = max(b["left"] + b["width"] for b in region)
            bottom = max(b["top"] + b["height"] for b in region)
            key = (page, amount, round(left / 6), round(top / 6))
            if key in seen:
                return
            seen.add(key)
            confs = [b["confidence"] for b in region]
            confidence = min(confs) if all(c is not None for c in confs) else None
            found.append(FinancialValue(
                source="PRINTED", amount=amount, page_number=page,
                barcode_index=None, raw_content=" ".join(b["text"] for b in region),
                provenance=provenance, left=left, top=top,
                width=right-left, height=bottom-top,
                confidence=confidence,
            ))

        def row_segments(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
            words = sorted(words, key=lambda b: (b["top"]+b["height"]/2, b["left"]))
            rows: list[list[dict[str, Any]]] = []
            for b in words:
                center = b["top"] + b["height"] / 2
                if rows:
                    base = rows[-1][0]
                    base_center = base["top"] + base["height"] / 2
                    if abs(center-base_center) <= max(6., min(12., min(b["height"],base["height"])*.7)):
                        rows[-1].append(b)
                        continue
                rows.append([b])
            segments: list[list[dict[str, Any]]] = []
            for row in rows:
                row.sort(key=lambda b: b["left"])
                segment: list[dict[str, Any]] = []
                for b in row:
                    if segment and b["left"] - (segment[-1]["left"]+segment[-1]["width"]) > 100:
                        segments.append(segment)
                        segment = []
                    segment.append(b)
                if segment:
                    segments.append(segment)
            return segments

        def bounds(region: list[dict[str, Any]]) -> tuple[float,float,float,float]:
            return (min(b["left"] for b in region),
                    min(b["top"] for b in region),
                    max(b["left"]+b["width"] for b in region),
                    max(b["top"]+b["height"] for b in region))

        for page, page_boxes in entries.items():
            segments = row_segments(page_boxes)
            labels: list[list[dict[str, Any]]] = []
            monies: list[tuple[list[dict[str, Any]], str]] = []
            for segment in segments:
                text = " ".join(b["text"] for b in segment)
                # Mais de um preço na região: não escolher o primeiro.
                money_candidates = re.findall(
                    r"(?<!\d)(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}(?!\d)", text,
                )
                if len(money_candidates) > 1:
                    continue
                # Rótulo e número reconstruídos de caixas-palavra da mesma linha.
                matches = list(cls._PRINTED_TOTAL_LOCAL.finditer(text))
                if len(matches) == 1:
                    provenance = "OCR_TEXT_BOX_LINE"
                    if len(segment) == 1:
                        provenance = "OCR_TEXT_BOX"
                    elif (len(segment) == 2 and cls._PRINTED_LABEL.search(segment[0]["text"])
                          and cls._MONEY_ONLY.fullmatch(segment[1]["text"])):
                        provenance = "OCR_TEXT_BOX_PAIR"
                    append(page, matches[0].group("amount"), segment, provenance)
                    continue
                if cls._PRINTED_LABEL.search(text):
                    labels.append(segment)
                money = cls._MONEY_ONLY.fullmatch(text)
                if money:
                    monies.append((segment, money.group("amount")))

            for label in labels:
                lx,ly,lr,lb = bounds(label)
                options: list[tuple[float, list[dict[str, Any]], str]] = []
                for candidate, amount in monies:
                    cx,cy,cr,cb = bounds(candidate)
                    lmid=(ly+lb)/2
                    cmid=(cy+cb)/2
                    same_row = (abs(lmid-cmid) <= max(9., min(lb-ly, cb-cy)*.9)
                                and cx >= lx and cx-lr <= 260)
                    overlap = min(lr,cr)-max(lx,cx)
                    vertical_gap = cy-lb
                    below = (0 <= vertical_gap <= max(36., 2.5*(lb-ly))
                             and overlap >= max(5., min(lr-lx,cr-cx)*.2))
                    if same_row or below:
                        options.append((abs(lmid-cmid) + abs(cx-lr)*.08,
                                        candidate, amount))
                # Duas opções candidatas exigem inspeção; não escolher por ordem.
                if len(options) != 1:
                    continue
                _, candidate, amount = options[0]
                append(page, amount, [*label, *candidate], "OCR_TEXT_BOX_PAIR")
        return found

    @classmethod
    def _compare_located_values(
        cls, values: list[FinancialValue],
    ) -> list[FinancialComparison]:
        """Compara observações por página; nunca presume a mesma cobrança."""
        by_page: dict[int, dict[str, list[FinancialValue]]] = {}
        for value in values:
            if value.page_number is None:
                continue
            if value.source == "PRINTED" and (
                value.confidence is None or
                value.confidence < cls._MIN_LOCAL_CONFIDENCE_FOR_COMPARISON
            ):
                continue
            by_page.setdefault(value.page_number, {}).setdefault(
                value.source, []
            ).append(value)
        output: list[FinancialComparison] = []
        for page, sources in sorted(by_page.items()):
            if len(sources) < 2:
                continue
            # Não comparar arbitrariamente um dos dois ITFs/QR distintos.
            if any(
                len({value.raw_content for value in sources.get(source, [])}) > 1
                for source in ("ITF", "PIX")
            ):
                continue
            amounts_by_source = {
                source: {value.amount for value in items}
                for source, items in sources.items()
                if source in ("ITF", "PIX", "PRINTED")
            }
            if len(amounts_by_source) < 2 or any(
                len(amounts) != 1 for amounts in amounts_by_source.values()
            ):
                continue
            ordered = tuple(source for source in ("ITF", "PIX", "PRINTED")
                            if source in amounts_by_source)
            amounts = tuple(next(iter(amounts_by_source[source])) for source in ordered)
            relation = "EQUAL_VALUES" if len(set(amounts)) == 1 else "DIFFERENT_VALUES"
            formatted = "; ".join(
                f"{source}=R$ {amount:.2f}".replace(".", ",")
                for source, amount in zip(ordered, amounts)
            )
            output.append(FinancialComparison(
                page_number=page, sources=ordered, amounts=amounts,
                relation=relation,
                message=(
                    f"Página {page}: {formatted}. "
                    "Valores observados na mesma página; vínculo com a "
                    "mesma cobrança ainda não demonstrado."
                ),
            ))
        return output

    @classmethod
    def _reconcile_evidence(
        cls, values: list[FinancialValue]
    ) -> tuple[FinancialReconciliationStatus, str]:
        """Reconcilia apenas um par único ITF/Pix na mesma página.

        A presença de vários instrumentos/quantias na mesma página é ambígua,
        não autoriza escolher um par pela ordem. Texto sem localização jamais
        altera o status para REVIEW_REQUIRED.
        """
        by_page: dict[int, dict[str, list[FinancialValue]]] = {}
        for value in values:
            if value.source not in ("ITF", "PIX") or value.page_number is None:
                continue
            by_page.setdefault(value.page_number, {"ITF": [], "PIX": []})[
                value.source
            ].append(value)

        reviewed = False
        consistent = False
        ambiguous = False
        for page, sources in sorted(by_page.items()):
            itfs = sources["ITF"]
            pixs = sources["PIX"]
            if not itfs or not pixs:
                continue
            itf_contents = {item.raw_content for item in itfs}
            pix_contents = {item.raw_content for item in pixs}
            # Mais de um código distinto por modalidade na página é ambíguo,
            # mesmo quando coincidentemente têm a mesma quantia.
            if len(itf_contents) != 1 or len(pix_contents) != 1:
                ambiguous = True
                continue
            if itfs[0].amount != pixs[0].amount:
                reviewed = True
            else:
                consistent = True

        if reviewed:
            return (
                FinancialReconciliationStatus.REVIEW_REQUIRED,
                "Valores diferentes em ITF e Pix legíveis na mesma página. "
                "Requer conferência da vinculação à cobrança; não comprova fraude.",
            )
        if ambiguous:
            return (
                FinancialReconciliationStatus.INCONCLUSIVE,
                "Há múltiplos instrumentos de pagamento na mesma página; "
                "não é seguro associá-los sem evidência contextual.",
            )
        if consistent:
            return (
                FinancialReconciliationStatus.CONSISTENT,
                "ITF e Pix da mesma página apresentam valores iguais; "
                "isso não atesta a autenticidade do documento.",
            )
        return (
            FinancialReconciliationStatus.INCONCLUSIVE,
            "Não há associação suficientemente documentada entre dois "
            "valores de pagamento para concluir a reconciliação.",
        )

    @classmethod
    def _read_collection_barcode(cls, content: str) -> tuple[Decimal | None, str | None]:
        """FEBRABAN arrecadação: 8, segmento, indicador, DV, 11 dígitos de valor.

        Indicadores 7 e 9 são quantidade/referência e NÃO centavos.
        Não interpreta código bancário de cobrança (outro layout).
        """
        if len(content) != 44 or not content.isascii() or not content.isdecimal():
            return None, None
        if content[0] != "8" or content[1] not in cls._SEGMENTS:
            return None, None
        reference = content[2]
        if reference not in "6789":
            return None, "Arrecadação com identificador de valor desconhecido"
        data = content[:3] + content[4:]
        calculator = (
            cls._modulo_10 if reference in "67" else cls._modulo_11_collection
        )
        expected = calculator(data)
        if int(content[3]) != expected:
            return None, "Dígito verificador geral da arrecadação inválido"
        if reference in cls._REFERENCE_VALUES:
            return None, "Quantidade/referência não corresponde a valor efetivo em reais"
        amount = Decimal(int(content[4:15])) / Decimal(100)
        return amount, None

    @staticmethod
    def _modulo_10(content: str) -> int:
        total, multiplier = 0, 2
        for char in reversed(content):
            value = int(char) * multiplier
            total += value // 10 + value % 10
            multiplier = 1 if multiplier == 2 else 2
        return (10 - total % 10) % 10

    @staticmethod
    def _modulo_11_collection(content: str) -> int:
        total, multiplier = 0, 2
        for char in reversed(content):
            total += int(char) * multiplier
            multiplier = 2 if multiplier == 9 else multiplier + 1
        remainder = total % 11
        if remainder in (0, 1):
            return 0
        if remainder == 10:
            return 1
        return 11 - remainder

    @classmethod
    def _read_pix_payload(cls, content: str) -> tuple[Decimal | None, str | None]:
        """BR Code EMV TLV validado localmente; sem chamadas externas.

        O comprimento TLV conta bytes (UTF-8), não caracteres Unicode.
        Apenas QR Pix identificado pelo GUI br.gov.bcb.pix é interpretado.
        """
        try:
            payload = content.encode("utf-8")
            fields = cls._parse_tlv(payload)
            if not fields or fields.get("00") != b"01":
                return None, None
            pix_found = False
            for tag in (f"{i:02d}" for i in range(26, 52)):
                merchant = fields.get(tag)
                if merchant is None:
                    continue
                parsed = cls._parse_tlv(merchant)
                if parsed and parsed.get("00", b"").lower() == b"br.gov.bcb.pix":
                    pix_found = True
                    break
            if not pix_found:
                return None, None
            if fields.get("53") != b"986" or fields.get("58") != b"BR":
                return None, "Pix com moeda ou país não suportado para reconciliação BRL"

            # CRC precisa ser o campo 63 final, comprimento 04, e cobrir
            # os bytes anteriores incluindo o prefixo '6304'.
            if len(payload) < 8 or payload[-8:-4] != b"6304":
                return None, "Pix sem CRC16 final válido"
            crc_received = payload[-4:]
            if not re.fullmatch(rb"[0-9A-Fa-f]{4}", crc_received):
                return None, "Pix com CRC16 malformado"
            crc_calculated = cls._crc16_ccitt(payload[:-4])
            if int(crc_received, 16) != crc_calculated:
                return None, "Pix com CRC16 divergente"

            field_54 = fields.get("54")
            if field_54 is None:
                return None, "Pix sem valor explícito no BR Code; valor não foi presumido"
            if not re.fullmatch(rb"[0-9]{1,10}(?:\.[0-9]{1,2})?", field_54):
                return None, "Pix com campo 54 malformado"
            amount = Decimal(field_54.decode("ascii"))
            if not amount.is_finite():
                return None, "Pix com valor não finito"
            return amount, None
        except (UnicodeError, ValueError, InvalidOperation):
            return None, "BR Code Pix com estrutura inválida"

    @staticmethod
    def _parse_tlv(payload: bytes) -> dict[str, bytes] | None:
        fields: dict[str, bytes] = {}
        position = 0
        while position < len(payload):
            if position + 4 > len(payload):
                return None
            header = payload[position:position + 4]
            if not all(48 <= x <= 57 for x in header):
                return None
            tag = header[:2].decode("ascii")
            length = int(header[2:].decode("ascii"))
            position += 4
            if length > len(payload) - position or tag in fields:
                return None
            fields[tag] = payload[position:position + length]
            position += length
        return fields

    @staticmethod
    def _crc16_ccitt(data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                crc = (
                    ((crc << 1) ^ 0x1021) & 0xFFFF
                    if crc & 0x8000 else
                    (crc << 1) & 0xFFFF
                )
        return crc

    @staticmethod
    def _parse_br_money(value: str) -> Decimal | None:
        try:
            amount = Decimal(value.replace(".", "").replace(",", "."))
            return amount if amount.is_finite() else None
        except InvalidOperation:
            return None

    @staticmethod
    def _normalize_format(fmt: Any) -> str:
        return re.sub(r"[^a-z0-9]", "", str(fmt or "").lower())

    @staticmethod
    def _positive_int(number: Any) -> int | None:
        return number if type(number) is int and number > 0 else None

    @staticmethod
    def _describe_issue(reason: str, page: int | None, index: int | None) -> str:
        return f"{reason} (página: {page if page is not None else '?'}; índice: {index if index is not None else '?'})"
