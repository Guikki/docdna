"""CF-QA 003.9.1: leitura conservadora de conteúdos textuais codificados.

Este serviço NÃO executa textos, não abre URLs e não consulta serviços externos.
A decodificação NÃO determina se um conteúdo é confiável ou malicioso.

API:
    inspector = EncodedContentInspector()
    findings = inspector.inspect([{"text": "01001000 ...", "page_number": 1}])

A saída é composta de dicionários simples para facilitar a futura integração
com a camada de evidências do DocDNA, sem alterar contratos já existentes.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
import unicodedata
from typing import Any, Iterable


class EncodedContentInspector:
    """Decodifica somente representações textuais estritamente reconhecíveis."""

    MAX_CANDIDATES = 256
    MAX_RAW_CHARS = 8192
    MAX_DECODED_BYTES = 4096
    MAX_DEPTH = 2
    _BINARY = re.compile(r"[01\s]+\Z")
    _HEXA = re.compile(r"(?:[0-9a-fA-F]{2}(?:[\s:]+)?)+\Z")
    _BASE64 = re.compile(r"[A-Za-z0-9+/]+={0,2}\Z")
    _QR_FONT = re.compile(r"(?:^|[^a-z])qr(?:code)?(?:[^a-z]|$)|qrcode", re.I)

    def inspect(self, observations: Iterable[Any]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for position, observation in enumerate(observations):
            if position >= self.MAX_CANDIDATES:
                break
            raw = self._value(observation, "text", None)
            if raw is None:
                raw = self._value(observation, "content", "")
            if not isinstance(raw, str) or not raw.strip():
                continue
            source = str(self._value(observation, "source", "native_text") or "native_text")
            font = str(self._value(observation, "font_name", "") or "")
            page = self._value(observation, "page_number", None)
            bbox = self._value(observation, "bounding_box", None)
            font_hint = self._is_qr_font(font)
            if len(raw) > self.MAX_RAW_CHARS:
                findings.append(self._finding(
                    raw, source, page, font, bbox, "ENCODED_CONTENT_OVERSIZE",
                    [], "Conteúdo acima do limite seguro de inspeção", font_hint))
                continue
            variants = self._decode_variants(raw)
            is_binary = self._binary_bits(raw) is not None
            if not (font_hint or is_binary or variants):
                continue
            if variants:
                code = "ENCODED_TEXT_DECODED"
                reason = "Texto recuperado de representação codificada; requer inspeção semântica separada"
            elif font_hint:
                code = "QR_FONT_CANDIDATE"
                reason = "Fonte com nome sugestivo de QR; sem confirmação de QR ou ocultação"
            else:
                code = "ENCODED_BINARY_UNRESOLVED"
                reason = "Sequência binária observada, sem decodificação textual confiável"
            findings.append(self._finding(raw, source, page, font, bbox, code, variants, reason, font_hint))
        return findings

    def prepare_qr_semantic_inputs(self, barcodes: Iterable[Any]) -> list[dict[str, Any]]:
        """Expõe payloads QR como DADOS não confiáveis para o detector existente.

        Não faz análise semântica por conta própria e nunca executa conteúdo.
        Preserva também o conteúdo original do QR, mesmo que não seja binário.
        """
        inputs: list[dict[str, Any]] = []
        for index, barcode in enumerate(barcodes):
            if index >= self.MAX_CANDIDATES:
                break
            fmt = re.sub(r"[^a-z0-9]", "", str(self._value(barcode, "format", "") or "").lower())
            if fmt not in ("qr", "qrcode"):
                continue
            value = self._value(barcode, "content", "")
            if not isinstance(value, str) or not value.strip():
                continue
            digest = hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
            source_metadata = {
                "source": "QR_DECODED_PAYLOAD",
                "page_number": self._value(barcode, "page_number", None),
                "barcode_index": self._value(barcode, "barcode_index", None),
                "untrusted": True,
            }
            if len(value) > self.MAX_RAW_CHARS:
                inputs.append({**source_metadata, "text": None, "sha256": digest,
                               "status": "SKIPPED_OVERSIZE", "encoding_chain": []})
                continue
            inputs.append({**source_metadata, "text": value, "sha256": digest,
                           "status": "REQUIRES_SEMANTIC_ANALYSIS", "encoding_chain": []})
            for decoded in self._decode_variants(value):
                inputs.append({**source_metadata, "text": decoded["text"],
                               "sha256": decoded["sha256"],
                               "status": "REQUIRES_SEMANTIC_ANALYSIS",
                               "encoding_chain": decoded["encoding_chain"]})
        return inputs

    def _decode_variants(self, raw: str) -> list[dict[str, Any]]:
        queue: list[tuple[str, tuple[str, ...]]] = [(raw.strip(), ())]
        visited: set[str] = {raw.strip()}
        variants: list[dict[str, Any]] = []
        while queue and len(variants) < 6:
            text, chain = queue.pop(0)
            if len(chain) >= self.MAX_DEPTH:
                continue
            for name, data in self._bytes_candidates(text):
                if len(data) > self.MAX_DECODED_BYTES:
                    continue
                decoded = self._readable_text(data)
                if decoded is None or decoded in visited:
                    continue
                visited.add(decoded)
                next_chain = chain + (name,)
                variants.append({
                    "encoding_chain": list(next_chain),
                    "text": decoded,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "byte_length": len(data),
                    "requires_semantic_review": True,
                })
                if len(next_chain) < self.MAX_DEPTH:
                    queue.append((decoded, next_chain))
        return variants

    def _bytes_candidates(self, text: str) -> list[tuple[str, bytes]]:
        answer: list[tuple[str, bytes]] = []
        bits = self._binary_bits(text)
        if bits is not None and len(bits) % 8 == 0:
            if len(bits) // 8 <= self.MAX_DECODED_BYTES:
                answer.append(("binary_8bit", bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))))
        value = text.strip()
        explicit_hex = value.lower().startswith("hex:")
        hex_body = value[4:].strip() if explicit_hex else value
        hex_clean = re.sub(r"[\s:]", "", hex_body)
        # Sem marcador, evitar interpretar identificadores numéricos como hex.
        if (explicit_hex or bool(re.search(r"[a-fA-F]", hex_clean))) and \
                8 <= len(hex_clean) <= self.MAX_DECODED_BYTES * 2 and \
                len(hex_clean) % 2 == 0 and self._HEXA.fullmatch(hex_body):
            try:
                answer.append(("hex", bytes.fromhex(hex_clean)))
            except ValueError:
                pass
        explicit_b64 = value.lower().startswith("base64:")
        b64 = value[7:].strip() if explicit_b64 else value
        # Marcador, padding ou símbolos dão evidência de que não é só um ID.
        has_marker = explicit_b64 or b64.endswith("=") or "+" in b64 or "/" in b64
        if has_marker and 12 <= len(b64) <= self.MAX_DECODED_BYTES * 2 and \
                len(b64) % 4 == 0 and self._BASE64.fullmatch(b64):
            try:
                answer.append(("base64", base64.b64decode(b64, validate=True)))
            except (ValueError, binascii.Error):
                pass
        return answer

    @classmethod
    def _binary_bits(cls, text: str) -> str | None:
        if not cls._BINARY.fullmatch(text):
            return None
        bits = "".join(text.split())
        return bits if len(bits) >= 32 else None

    @staticmethod
    def _readable_text(data: bytes) -> str | None:
        if not 4 <= len(data) <= EncodedContentInspector.MAX_DECODED_BYTES:
            return None
        try:
            result = data.decode("utf-8", errors="strict")
        except UnicodeError:
            return None
        if not result.strip() or len(result) < 4:
            return None
        readable = sum(c.isprintable() or c in "\n\r\t" for c in result)
        if readable / len(result) < 0.95:
            return None
        letters = [c.casefold() for c in result if unicodedata.category(c).startswith("L")]
        if len(letters) < 3 or len(set(letters)) < 3:
            # Matrizes repetitivas (ex.: 010101... -> UUUUU...) não são texto.
            return None
        return result

    @classmethod
    def _is_qr_font(cls, font_name: str) -> bool:
        # 'VivoQRCode' funciona como pista, mas nunca como prova de conteúdo QR.
        return bool(cls._QR_FONT.search(font_name))

    @staticmethod
    def _value(observation: Any, name: str, default: Any) -> Any:
        if isinstance(observation, dict):
            return observation.get(name, default)
        return getattr(observation, name, default)

    @staticmethod
    def _finding(
        raw: str, source: str, page: Any, font: str, bbox: Any,
        code: str, variants: list[dict[str, Any]], reason: str, font_hint: bool,
    ) -> dict[str, Any]:
        return {
            "code": code,
            "source": source,
            "page_number": page,
            "font_name": font or None,
            "bounding_box": bbox,
            "raw_sha256": hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest(),
            "raw_length": len(raw),
            "raw_preview": raw[:120],
            "qr_font_hint": font_hint,
            "qr_confirmed": False,
            "visually_concealed": None,
            "decoded": variants,
            "reason": reason,
            # O conteúdo decodificado pode ter sido introduzido por um adversário.
            # Deve ser encaminhado como DADO, jamais como instrução executável.
            "semantic_inspection_required": bool(variants),
        }
