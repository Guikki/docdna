"""CF-QA 003.6 — extração conservadora e comparação de identificadores.

Não usa regras por operadora. Captura somente campos acompanhados de rótulo;
não confunde qualquer sequência de dígitos com conta/fatura. Leituras OCR
continuam observações e NÃO são provas de fraude.
"""
from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace
import re
from statistics import median
from typing import Any, Iterable


class DocumentIdentifierService:
    # Nomes persistidos são parte do contrato de exportação.
    LABELS = {
        "account": "Número da conta",
        "customer": "Código do cliente",
        "invoice": "Número da fatura",
        "automatic_debit": "Débito automático",
        "holder": "Titular informado",
    }

    _PATTERNS = {
        "account": re.compile(
            r"(?<!\w)(?:n[º°o.]?\s*(?:da\s+)?conta|n[uú]mero\s+da\s+conta|"
            r"conta\s*(?:n[º°o.]?|n[uú]mero)?)\s*[:#\-.]?\s*"
            r"(?P<value>\d[\d.\-/ ]{4,29}\d)(?!\d)", re.I),
        "customer": re.compile(
            r"(?<!\w)(?:c[oó]d(?:igo)?\.?\s*(?:do\s+)?cliente|"
            r"cliente\s*(?:n[º°o.]?|c[oó]digo)?)\s*[:#\-.]?\s*"
            r"(?P<value>\d[\d.\-/ ]{4,29}\d)(?!\d)", re.I),
        "invoice": re.compile(
            r"(?<!\w)(?:n[º°o.]?\s*(?:da\s+)?fatura|"
            r"n[uú]mero\s+da\s+fatura|fatura\s*(?:n[º°o.]?|n[uú]mero)?)"
            r"\s*[:#\-.]?\s*(?P<value>\d[\d.\-/ ]{4,29}\d)(?!\d)", re.I),
        "automatic_debit": re.compile(
            r"(?<!\w)(?:(?:c[oó]d(?:igo)?\.?\s*(?:de\s+)?)?"
            r"d[eé]bito\s+autom[aá]tico)\s*[:#\-.]?\s*"
            r"(?P<value>\d[\d.\-/ ]{4,29}\d)(?!\d)", re.I),
        "holder": re.compile(
            r"(?<!\w)(?:titular|nome\s+do\s+cliente|nome\s+do\s+titular|cliente|nome\s+do\s+assinante)"
            r"\s*[:\-]\s*(?P<value>[A-ZÀ-Ü][A-Za-zÀ-ÿ' -]{5,75})", re.I),
    }
    _NON_DIGITS = re.compile(r"\D")
    _MAX_ITEMS = 200  # limite por documento; bloqueia OCRs patológicos
    _MAX_MATCHES = 3000  # evita explosão quadrática em lotes extensos

    def extract(
        self, *, ocr_text_boxes: Iterable[Any] = (),
        native_text: Any = None, ocr: Any = None,
        normalized_document: Any = None,
    ) -> list[dict[str, Any]]:
        """Retorna apenas rótulos encontrados, nunca valores inferidos.

        A geometria de OCR é mantida em pixels da renderização utilizada.
        Texto agregado permanece SEM página e SEM coordenadas.
        """
        observations: list[dict[str, Any]] = []
        # OcrReader emite uma caixa por palavra, não uma caixa por campo.
        ocr_boxes = list(ocr_text_boxes or ())
        for page, line_boxes in self._visual_lines(ocr_boxes):
            # Colunas afastadas na mesma altura não são um único campo.
            for segment in self._split_distant_boxes(line_boxes):
                text = " ".join(str(self._get(box, "text", "") or "") for box in segment)
                confidences = [self._number(self._get(box, "confidence")) for box in segment]
                confidences = [v for v in confidences if v is not None]
                geometries = [
                    (self._number(self._get(box, "left")), self._number(self._get(box, "top")),
                     self._number(self._get(box, "width")), self._number(self._get(box, "height")))
                    for box in segment
                ]
                geometries = [(x,y,w,h) for x,y,w,h in geometries if None not in (x,y,w,h)]
                left = min((b[0] for b in geometries), default=None)
                top = min((b[1] for b in geometries), default=None)
                right = max((b[0]+b[2] for b in geometries), default=None)
                bottom = max((b[1]+b[3] for b in geometries), default=None)
                for item in self._scan_text(text):
                    observations.append({**item, "source": "OCR_BOX", "page_number": page,
                        "left": left, "top": top,
                        "width": (right-left) if right is not None and left is not None else None,
                        "height": (bottom-top) if bottom is not None and top is not None else None,
                        "confidence": min(confidences) if confidences else None})
                    if len(observations) >= self._MAX_ITEMS:
                        return self._deduplicate(observations)

        # Layout de tabela/canhoto: rótulos na linha de cima, valores embaixo.
        remaining = max(0, self._MAX_ITEMS - len(observations))
        observations.extend(self._extract_stacked_fields(ocr_boxes)[:remaining])
        observations.extend(self._extract_native_fields(normalized_document)[
            :max(0, self._MAX_ITEMS - len(observations))
        ])

        # Fallback agregado: não atribuir página/posição inexistentes.
        for source, document in (("NATIVE_AGGREGATED", native_text), ("OCR_AGGREGATED", ocr)):
            content = str(self._get(document, "content", "") or "")
            for line in content.splitlines():
                for item in self._scan_text(line):
                    observations.append({**item, "source": source, "page_number": None,
                        "left": None, "top": None, "width": None, "height": None,
                        "confidence": None})
                    if len(observations) >= self._MAX_ITEMS:
                        return self._deduplicate(observations)
        return self._deduplicate(observations)

    @staticmethod
    def _native_boxes(document: Any) -> list[Any]:
        boxes = []
        for page in getattr(document, "pages", ()) or ():
            for span in getattr(page, "text_spans", ()) or ():
                box = getattr(span, "bounding_box", None)
                if box is None:
                    continue
                boxes.append(SimpleNamespace(
                    text=span.text, page_number=span.page_number,
                    left=box.left * 2, top=box.top * 2,
                    width=(box.right-box.left) * 2, height=(box.bottom-box.top) * 2,
                    confidence=100,
                ))
        return boxes

    def _extract_native_fields(self, document: Any) -> list[dict[str, Any]]:
        boxes = self._native_boxes(document)
        if not boxes:
            return []
        # Reutiliza a mesma associação/exclusividade em escala equivalente à
        # renderização OCR; devolve a geometria nativa em pontos de PDF.
        items = self.extract(ocr_text_boxes=boxes)
        for item in items:
            item.update(source="NATIVE_SPAN", confidence=None, coordinate_system="pdf_points")
            for key in ("left", "top", "width", "height"):
                if item.get(key) is not None:
                    item[key] /= 2
            if item.get("value_region"):
                item["value_region"] = {k: v / 2 for k, v in item["value_region"].items()}
        return items

    def propose_ocr_regions(self, boxes: Iterable[Any], observations: list[dict]) -> list[dict]:
        """Propõe recortes por cabeçalhos; não fornece nem infere seus valores.

        Orçamento local de quatro regiões por documento. A leitura original
        permanece disponível quando não há suporte para recuperação localizada.
        """
        groups = []
        for page, row in self._visual_lines(boxes):
            text = " ".join(str(self._get(b, "text", "")) for b in row)
            kinds = {k for k, p in self._HEADER_LABELS.items() if k != "holder" and p.search(text)}
            if not kinds:
                continue
            top = min(float(self._get(b, "top")) for b in row)
            bottom = max(float(self._get(b, "top"))+float(self._get(b, "height")) for b in row)
            if groups and groups[-1]["page"] == page and top < groups[-1]["bottom"]:
                groups[-1]["boxes"].extend(row)
                groups[-1]["kinds"].update(kinds)
                groups[-1]["bottom"] = max(bottom, groups[-1]["bottom"])
            else:
                groups.append({"page": page, "boxes": list(row), "kinds": kinds,
                               "top": top, "bottom": bottom})
        regions = []
        for group in groups:
            known = {f.get("kind") for f in observations if f.get("page_number") == group["page"]}
            missing = group["kinds"] - known
            if len(group["kinds"]) < 2 or not missing:
                continue
            row = group["boxes"]
            height = median(float(self._get(b, "height")) for b in row)
            if height <= 0:
                continue
            left = min(float(self._get(b, "left")) for b in row)
            right = max(float(self._get(b, "left"))+float(self._get(b, "width")) for b in row)
            regions.append({"page_number": group["page"], "missing_kinds": sorted(missing),
                            "bounds_ocr_pixels": (max(0, left-2*height), max(0, group["top"]-height),
                                                  right+2*height, group["bottom"]+3*height)})
            if len(regions) == 4:
                break
        return regions

    def annotate_region_conflicts(self, observations: list[dict], original_boxes: Iterable[Any]) -> list[dict]:
        """Confronta leituras na mesma célula sem corrigir ou escolher dígitos."""
        boxes = list(original_boxes)
        for item in observations:
            region = item.get("value_region")
            if not region:
                continue
            alternatives = []
            for box in boxes:
                if self._get(box, "page_number") != item.get("page_number"):
                    continue
                text = str(self._get(box, "text", "") or "")
                digits = self._NON_DIGITS.sub("", text)
                if not 6 <= len(digits) <= 24 or re.search(r"[A-Za-z]", text):
                    continue
                x, y, width, height = (float(self._get(box, k)) for k in ("left", "top", "width", "height"))
                overlap = (max(0, min(x+width, region["left"]+region["width"])-max(x, region["left"]))
                           * max(0, min(y+height, region["top"]+region["height"])-max(y, region["top"])))
                area = min(width*height, region["width"]*region["height"])
                if area > 0 and overlap / area >= .5 and digits != item["value"]:
                    alternatives.append({"value": digits, "raw_excerpt": text, "source": "OCR_BOX",
                                         "confidence": self._get(box, "confidence"),
                                         "left": x, "top": y, "width": width, "height": height})
            if alternatives:
                item.update(reading_conflict=True, alternative_readings=alternatives,
                            review_reason="OCR integral e OCR localizado divergem na mesma célula; conferir original.")
        return observations

    # Fragmentos sem valor, exclusivamente para associar um cabeçalho a uma
    # célula imediatamente abaixo. Não inferir números sem rótulo.
    _HEADER_LABELS = {
        "account": re.compile(
            r"(?<!\w)(?:n[º°o.]?\s*(?:da\s+)?conta|n[uú]mero\s+da\s+conta|conta)(?!\w)", re.I),
        "customer": re.compile(
            r"(?<!\w)(?:c[oó]d(?:igo)?\.?\s*(?:do\s+)?cliente|cliente)(?!\w)", re.I),
        "invoice": re.compile(
            r"(?<!\w)(?:n[º°o.]?\s*(?:da\s+)?fatura|n[uú]mero\s+da\s+fatura|fatura)(?!\w)", re.I),
        "automatic_debit": re.compile(
            r"(?<!\w)(?:(?:c[oó]d(?:igo)?\.?\s*(?:de\s+)?)?d[eé]bito\s+autom[aá]tico)(?!\w)", re.I),
        "holder": re.compile(r"(?<!\w)(?:titular|nome\s+do\s+titular|nome\s+do\s+assinante)(?!\w)", re.I),
    }
    _STACKED_DIGITS = re.compile(r"^[0-9][0-9.\-/ ]{4,34}[0-9]$")
    _STACKED_NAME = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' -]{5,75}$")

    def _extract_stacked_fields(self, boxes: list[Any]) -> list[dict[str, Any]]:
        """Associa cabeçalhos a células na linha inferior por proximidade X/Y.

        Uma linha pode conter vários cabeçalhos, sem uma relação de colunas
        pré-conhecida. Uma associação ambígua é descartada; não assumimos
        que a primeira sequência numérica da página é uma conta.
        """
        by_page: dict[int, list[list[Any]]] = defaultdict(list)
        for page, line in self._visual_lines(boxes):
            by_page[page].append(line)

        results: list[dict[str, Any]] = []
        for page, rows in by_page.items():
            labels: list[dict[str, Any]] = []
            candidates: list[dict[str, Any]] = []
            for row_index, row in enumerate(rows):
                words = sorted(row, key=lambda b: self._number(self._get(b, "left")) or 0)
                text_parts = [str(self._get(b, "text", "") or "") for b in words]
                text = " ".join(text_parts)
                spans: list[tuple[int, int, Any]] = []
                pos = 0
                for word, box in zip(text_parts, words):
                    spans.append((pos, pos+len(word), box))
                    pos += len(word)+1
                for kind, regex in self._HEADER_LABELS.items():
                    for match in regex.finditer(text):
                        # Evita coincidências dentro de campos já preenchidos.
                        # A associação empilhada só procura a linha INFERIOR.
                        matched = [b for a,z,b in spans if a < match.end() and z > match.start()]
                        if not matched:
                            continue
                        x = min(float(self._get(b,"left")) for b in matched)
                        right = max(float(self._get(b,"left"))+float(self._get(b,"width")) for b in matched)
                        y = min(float(self._get(b,"top")) for b in matched)
                        bottom = max(float(self._get(b,"top"))+float(self._get(b,"height")) for b in matched)
                        labels.append({"kind":kind, "row":row_index, "boxes":matched,
                                       "left":x, "right":right, "top":y, "bottom":bottom})

                # Um token OCR já contém frequentemente a célula numérica
                # INTEIRA. Não juntar duas células adjacentes mesmo quando o
                # espaço entre elas é de 35 px ou menos (canhotos estreitos).
                # Fragmentos curtos continuam agrupáveis quando não constituem
                # uma célula individual inequívoca.
                segments: list[list[Any]] = []
                for word in words:
                    x = self._number(self._get(word, "left"))
                    width = self._number(self._get(word, "width"))
                    if x is None or width is None:
                        continue
                    token = str(self._get(word, "text", "") or "").strip(" .-/")
                    token_digits = self._NON_DIGITS.sub("", token)
                    is_full_cell = bool(
                        self._STACKED_DIGITS.fullmatch(token)
                        and 6 <= len(token_digits) <= 24
                    )
                    if not segments:
                        segments.append([word])
                        continue
                    last = segments[-1][-1]
                    end_x = float(self._get(last, "left")) + float(self._get(last, "width"))
                    previous_token = str(self._get(last, "text", "") or "").strip(" .-/")
                    previous_digits = self._NON_DIGITS.sub("", previous_token)
                    previous_full = bool(
                        self._STACKED_DIGITS.fullmatch(previous_token)
                        and 6 <= len(previous_digits) <= 24
                    )
                    if is_full_cell or previous_full or x-end_x > 35:
                        segments.append([word])
                    else:
                        segments[-1].append(word)
                for segment in segments:
                    candidate_text = " ".join(str(self._get(b,"text","") or "") for b in segment).strip()
                    raw = candidate_text.strip(" .-/")
                    digits = self._NON_DIGITS.sub("", raw)
                    numeric = bool(self._STACKED_DIGITS.fullmatch(raw) and 6<=len(digits)<=24)
                    name = bool(self._STACKED_NAME.fullmatch(raw) and len(raw.split())>=2
                                and not any(c.isdigit() for c in raw))
                    if not numeric and not name:
                        continue
                    left = min(float(self._get(b,"left")) for b in segment)
                    right = max(float(self._get(b,"left"))+float(self._get(b,"width")) for b in segment)
                    top = min(float(self._get(b,"top")) for b in segment)
                    bottom = max(float(self._get(b,"top"))+float(self._get(b,"height")) for b in segment)
                    candidates.append({"row":row_index,"boxes":segment,"text":raw,
                        "digits":digits,"numeric":numeric,"name":name,
                        "left":left,"right":right,"top":top,"bottom":bottom})

            # Atribuição exclusiva: cada candidato só pode sustentar um campo.
            options: list[tuple[float, int, int]] = []
            for li, label in enumerate(labels):
                for ci, cand in enumerate(candidates):
                    if cand["row"] <= label["row"]:
                        continue
                    if label["kind"] == "holder" and not cand["name"]:
                        continue
                    if label["kind"] != "holder" and not cand["numeric"]:
                        continue
                    vertical_gap = cand["top"]-label["bottom"]
                    if vertical_gap < 0 or vertical_gap > 54:
                        continue
                    overlap = min(label["right"],cand["right"])-max(label["left"],cand["left"])
                    if overlap < max(5., .2*min(label["right"]-label["left"],
                                               cand["right"]-cand["left"])):
                        continue
                    xcent = (label["left"]+label["right"])/2
                    ccent = (cand["left"]+cand["right"])/2
                    score = abs(xcent-ccent)+2*vertical_gap
                    options.append((score,li,ci))
            # Não escolher quando a atribuição tem duas alternativas próximas.
            by_label: dict[int, list[tuple[float,int]]] = defaultdict(list)
            by_candidate: dict[int, list[tuple[float,int]]] = defaultdict(list)
            for score,li,ci in options:
                by_label[li].append((score,ci))
                by_candidate[ci].append((score,li))
            for li, choices in by_label.items():
                choices.sort()
                score,ci = choices[0]
                if len(choices)>1 and choices[1][0]-score < 18:
                    continue
                reversed_choices=sorted(by_candidate[ci])
                if reversed_choices[0][1]!=li or (len(reversed_choices)>1
                    and reversed_choices[1][0]-reversed_choices[0][0] < 18):
                    continue
                label,cand=labels[li],candidates[ci]
                involved=[*label["boxes"],*cand["boxes"]]
                confidence_values=[self._number(self._get(b,"confidence")) for b in involved]
                confidence=min(confidence_values) if all(v is not None for v in confidence_values) else None
                kind=label["kind"]
                value=(re.sub(r"\s+"," ",cand["text"]).strip().upper()
                       if kind=="holder" else cand["digits"])
                results.append({"kind":kind,"label":self.LABELS[kind],"value":value,
                    "coordinate_system":"ocr_pixels",
                    "value_region":{"left":cand["left"], "top":cand["top"],
                                    "width":cand["right"]-cand["left"],
                                    "height":cand["bottom"]-cand["top"]},
                    "raw_excerpt":" ".join(str(self._get(b,"text","")) for b in involved)[:120],
                    "source":"OCR_BOX","page_number":page,
                    "left":min(float(self._get(b,"left")) for b in involved),
                    "top":min(float(self._get(b,"top")) for b in involved),
                    "width":max(float(self._get(b,"left"))+float(self._get(b,"width")) for b in involved)
                            -min(float(self._get(b,"left")) for b in involved),
                    "height":max(float(self._get(b,"top"))+float(self._get(b,"height")) for b in involved)
                             -min(float(self._get(b,"top")) for b in involved),
                    "confidence":confidence})
        return results

    def compare(self, analyses: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """Coincidências EXATAS por tipo + possíveis mudanças de um dígito.

        Relações aproximadas exigem OCR >=80 ou texto nativo. A ausência de
        titular não autoriza classificar a coincidência como fraude.
        """
        documents: dict[str, dict] = {}
        by_kind: dict[str, dict[str, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
        for analysis in analyses:
            if not isinstance(analysis, dict):
                continue
            analysis_id = str(analysis.get("id") or analysis.get("analysis_id") or "")
            if not analysis_id:
                continue
            name = str(analysis.get("original_filename") or analysis.get("filename") or analysis_id)
            raw = analysis.get("document_identifiers") or []
            if not isinstance(raw, list):
                continue
            holders = {str(x.get("value")) for x in raw if isinstance(x,dict) and x.get("kind") == "holder"}
            owner = next(iter(holders)) if len(holders) == 1 else None
            documents[analysis_id] = {"filename": name, "holder": owner}
            distinct: dict[str, set[str]] = defaultdict(set)
            for obs in raw:
                if isinstance(obs, dict) and obs.get("kind") in self.LABELS and obs.get("kind") != "holder":
                    distinct[obs["kind"]].add(str(obs.get("value", "")))
            for obs in raw:
                if not isinstance(obs, dict):
                    continue
                if obs.get("reading_conflict"):
                    continue
                kind = str(obs.get("kind") or "")
                value = str(obs.get("value") or "")
                if kind not in self.LABELS or kind == "holder" or len(distinct[kind]) != 1:
                    continue  # valores conflitantes dentro do documento: não comparar
                existing = by_kind[kind][value].get(analysis_id)
                if existing is None or self._quality(obs) > self._quality(existing):
                    by_kind[kind][value][analysis_id] = obs

        results: list[dict[str, Any]] = []
        for kind, groups in by_kind.items():
            for value, occurrence_by_doc in groups.items():
                if len(occurrence_by_doc) < 2:
                    continue
                records = self._participants(occurrence_by_doc, documents)
                results.append(self._finding(kind, "EXACT", value, None, records))
                if len(results) >= self._MAX_MATCHES:
                    return results

            # Índice de variantes com um dígito substituído, O(n * tamanho).
            # Não produz todos-contra-todos entre centenas de documentos.
            variants: dict[tuple[int, str], set[str]] = defaultdict(set)
            for value in groups:
                if not (6 <= len(value) <= 24 and value.isascii() and value.isdecimal()):
                    continue
                for position in range(len(value)):
                    variants[(len(value), value[:position] + "*" + value[position+1:])].add(value)
            checked: set[tuple[str, str]] = set()
            for members in variants.values():
                if len(members) != 2:
                    continue  # >2 é colidir padrão comum; não especular pares
                a, b = sorted(members)
                pair_key = (a,b)
                if pair_key in checked:
                    continue
                checked.add(pair_key)
                ao, bo = groups[a], groups[b]
                if not (set(ao).isdisjoint(bo)):
                    continue
                if not all(self._quality(obs) >= 80 for obs in [*ao.values(), *bo.values()]):
                    continue
                records = self._participants({**ao, **bo}, documents)
                results.append(self._finding(kind, "ONE_DIGIT", a, b, records))
                if len(results) >= self._MAX_MATCHES:
                    return results
            # Troca de dígitos adjacentes: exatamente uma transposição.
            for a, ao in groups.items():
                if not (6 <= len(a) <= 24 and a.isascii() and a.isdecimal()):
                    continue
                for i in range(len(a)-1):
                    if a[i] == a[i+1]:
                        continue
                    b = a[:i] + a[i+1] + a[i] + a[i+2:]
                    if b not in groups or a >= b or (a,b) in checked:
                        continue
                    checked.add((a,b))
                    bo = groups[b]
                    if not set(ao).isdisjoint(bo):
                        continue
                    if not all(self._quality(obs) >= 80 for obs in [*ao.values(), *bo.values()]):
                        continue
                    results.append(self._finding(kind, "TRANSPOSITION", a, b,
                        self._participants({**ao, **bo}, documents)))
                    if len(results) >= self._MAX_MATCHES:
                        return results
        return results

    def _scan_text(self, text: str) -> list[dict[str, str]]:
        extracted = []
        for kind, pattern in self._PATTERNS.items():
            for match in pattern.finditer(text):
                raw = match.group("value").strip(" .-/")
                if kind == "holder":
                    value = re.sub(r"\s+", " ", raw).strip().upper()
                    if len(value.split()) < 2 or any(char.isdigit() for char in value):
                        continue
                    # Não absorver outro rótulo da mesma linha.
                    value = re.split(r"\s{2,}|\s+(?:CONTA|CLIENTE|FATURA|D[EÉ]BITO)\s*[:#]",value)[0].strip()
                else:
                    value = self._NON_DIGITS.sub("", raw)
                    if not (6 <= len(value) <= 24):
                        continue
                extracted.append({"kind": kind, "label": self.LABELS[kind],
                    "value": value, "raw_excerpt": match.group(0).strip()[:120]})
        return extracted

    def _visual_lines(self, boxes: Iterable[Any]):
        by_page: dict[int, list[Any]] = defaultdict(list)
        for box in boxes:
            page = self._get(box, "page_number")
            top = self._number(self._get(box, "top"))
            if type(page) is int and page > 0 and top is not None:
                by_page[page].append(box)
        for page in sorted(by_page):
            lines: list[list[Any]] = []
            for box in sorted(by_page[page], key=lambda b: (self._number(self._get(b,"top")) or 0,
                                                          self._number(self._get(b,"left")) or 0)):
                top = float(self._get(box, "top"))
                height = self._number(self._get(box, "height")) or 14
                # Ordem vertical já está classificada: basta comparar com
                # a última linha; não percorrer todas as linhas da página.
                if lines and abs(top - float(self._get(lines[-1][0], "top"))) <= min(10, max(4, height*.4)):
                    lines[-1].append(box)
                else:
                    lines.append([box])
            for line in lines:
                yield page, sorted(line, key=lambda b: self._number(self._get(b,"left")) or 0)

    def _deduplicate(self, items: list[dict]) -> list[dict]:
        # Ocorrências em páginas diferentes são mantidas; conteúdo agregado
        # equivalente é descartado se já existe OCR localizado.
        localized = {(x["kind"], x["value"]) for x in items if x.get("page_number")}
        seen: dict[tuple[str,str,int|None], dict] = {}
        for item in items:
            base = item["kind"], item["value"]
            if item.get("page_number") is None and base in localized:
                continue
            key = (*base, item.get("page_number"))
            if (key not in seen or self._quality(item) > self._quality(seen[key])
                    or (self._quality(item) == self._quality(seen[key])
                        and item.get("value_region") and not seen[key].get("value_region"))):
                seen[key] = item
        return list(seen.values())

    @classmethod
    def _split_distant_boxes(cls, boxes: list[Any]) -> list[list[Any]]:
        segments: list[list[Any]] = []
        for box in boxes:
            x = cls._number(cls._get(box, "left"))
            if not segments or x is None:
                segments.append([box])
                continue
            previous = segments[-1][-1]
            px = cls._number(cls._get(previous, "left"))
            pw = cls._number(cls._get(previous, "width"))
            if px is None or pw is None or x - (px + pw) > 140:
                segments.append([box])
            else:
                segments[-1].append(box)
        return segments

    @staticmethod
    def _get(obj: Any, key: str, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if obj is not None else default

    @staticmethod
    def _number(value):
        try:
            result = float(value)
            return result if 0 <= result <= 1000000 else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _quality(cls, obs: dict) -> float:
        source = str(obs.get("source") or "")
        if source == "NATIVE_SPAN":
            return 100.0
        if source == "NATIVE_AGGREGATED":
            # Sem página/coords, não autoriza afirmação de quase-igualdade.
            return 65.0
        if source in {"OCR_BOX", "OCR_REGION"}:
            conf = cls._number(obs.get("confidence"))
            return conf if conf is not None else 0
        return 0.0

    @staticmethod
    def _participants(occurrences: dict[str,dict], docs: dict) -> list[dict]:
        return [{"analysis_id": aid, "filename": docs[aid]["filename"],
                 "holder": docs[aid]["holder"], "page_number": obs.get("page_number"),
                 "source": obs.get("source"), "confidence": obs.get("confidence"),
                 "raw_excerpt": obs.get("raw_excerpt"), "value": obs.get("value")}
                for aid, obs in sorted(occurrences.items()) if aid in docs]

    def _finding(self, kind: str, relation: str, value: str, other: str | None,
                 participants: list[dict]) -> dict:
        owners = {x["holder"] for x in participants if x["holder"]}
        different_owners = len(owners) >= 2
        code = {"EXACT":"DOCUMENT_IDENTIFIER_EXACT_MATCH",
                "ONE_DIGIT":"DOCUMENT_IDENTIFIER_ONE_DIGIT",
                "TRANSPOSITION":"DOCUMENT_IDENTIFIER_TRANSPOSITION"}[relation]
        label = self.LABELS[kind]
        description = (f"{label}: {'mesmo valor observado' if relation == 'EXACT' else 'valores semelhantes observados'} "
                       f"em {len(participants)} documento(s). "
                       + ("Titulares informados distintos; verificar vínculo contratual. " if different_owners else
                          "Vínculo entre titulares não demonstrado. ")
                       + "Coincidência não comprova adulteração.")
        return {"code":code, "kind":kind, "label":label, "relation":relation,
                "value":value, "other_value":other, "description": description,
                "participants":participants, "document_count":len(participants),
                "severity":"Revisão recomendada" if different_owners and relation == "EXACT" else "Informativo"}
