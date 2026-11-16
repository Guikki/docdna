
"""CF-QA 003.9.5: correlação de matriz QR nativa com QR visual já lido.

Complementa (não substitui) QrStructuralInspector e BarcodeReader.

Condições para CONFIRMED_PAYLOAD_MATCH:
  - os bits provêm de um grupo nativo completo (sem truncamento);
  - uma matriz candidata tem localizadores, separadores e sincronização coerentes;
  - ZXing decodifica um QR da matriz reconstruída;
  - o SHA-256 do payload coincide com um QR visual associado geometricamente.

Um QR decodificado NÃO demonstra ocultação, fraude ou ausência de Prompt Injection.
Este módulo não executa payloads, não abre URLs e não reabre o PDF.
"""
from __future__ import annotations

from hashlib import sha256
from math import isqrt
from typing import Any

from app.domain.services.qr_matrix_inspector import QrMatrixInspector


class QrMatrixPayloadCorrelator:
    """Correlaciona bits de fonte PDF e QR já lido, sem revelar o payload."""

    MAX_QUIET_MODULES = 12
    MAX_BITS = (QrMatrixInspector.MAX_SIZE + 2 * MAX_QUIET_MODULES) ** 2
    MAX_FRAGMENTS = QrMatrixInspector.MAX_FRAGMENTS

    def inspect(
        self,
        *,
        group: dict[str, Any],
        linked_qr_codes: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": "NOT_CONFIRMED",
            "matrix_decoded": False,
            "matrix_pattern_candidate": False,
            "payload_equal_to_linked_qr": None,
            "decoded_payload_sha256": None,
            "decoded_byte_length": None,
            "matrix_dimension": None,
            "matrix_version": None,
            "matrix_outer_dimension": None,
            "quiet_zone_modules": None,
            "orientation": None,
            "inverted": None,
            "matching_linked_qr_count": 0,
            "visually_concealed": None,
        }
        if not isinstance(group, dict) or group.get("truncated"):
            return result
        raw = group.get("texts")
        if not isinstance(raw, (tuple, list)) or len(raw) > self.MAX_FRAGMENTS:
            return result
        if any(not isinstance(fragment, str) or any(c not in "01 \t\r\n" for c in fragment) for fragment in raw):
            return result
        fragments = tuple("".join(fragment.split()) for fragment in raw)
        bits = "".join(fragments)
        size = isqrt(len(bits))
        if not bits or len(bits) > self.MAX_BITS or size * size != len(bits):
            return result
        # Só reconstruímos em ordem de leitura se houver linhas completas,
        # ou um único stream; outros agrupamentos permanecem inconclusivos.
        if not (len(fragments) == size and all(len(line) == size for line in fragments)) and len(fragments) != 1:
            return result
        outer = tuple(bits[y * size:(y + 1) * size] for y in range(size))
        result["matrix_outer_dimension"] = size

        for orientation, inverted, candidate in QrMatrixInspector._orientations(outer):
            # O módulo pode ser uma matriz sem margem, ou uma matriz convencional
            # dentro de uma quiet zone clara e simétrica (incluída na fonte).
            for margin in range(0, min(self.MAX_QUIET_MODULES, (size - 21) // 2) + 1):
                inner_size = size - 2 * margin
                if not QrMatrixInspector._valid_dimension(inner_size):
                    continue
                if margin and not self._is_clear_quiet_zone(candidate, margin):
                    continue
                core = (
                    tuple(row[margin:size-margin] for row in candidate[margin:size-margin])
                    if margin else candidate
                )
                if not self._fixed_patterns_ok(core):
                    continue
                result["matrix_pattern_candidate"] = True
                result["status"] = "QR_MATRIX_CANDIDATE_UNCONFIRMED"
                # A validação estrita do projeto pode rejeitar QRs personalizados
                # ou com correção de erros. O decodificador independente é que
                # precisa recuperar o payload antes de qualquer confirmação.
                decoded = self._decode_qr(core)
                if decoded is None:
                    continue
                payload_sha = sha256(decoded.encode("utf-8", errors="replace")).hexdigest()
                matches = sum(
                    1 for item in linked_qr_codes
                    if isinstance(item, dict) and item.get("content_sha256") == payload_sha
                )
                result.update({
                    "status": "CONFIRMED_PAYLOAD_MATCH" if matches else "QR_DECODED_NO_LINKED_PAYLOAD_MATCH",
                    "matrix_decoded": True,
                    "payload_equal_to_linked_qr": True if matches else None,
                    "decoded_payload_sha256": payload_sha,
                    "decoded_byte_length": len(decoded.encode("utf-8", errors="replace")),
                    "matrix_dimension": inner_size,
                    "matrix_version": (inner_size - 17) // 4,
                    "quiet_zone_modules": margin,
                    "orientation": orientation,
                    "inverted": inverted,
                    "matching_linked_qr_count": matches,
                })
                return result
        return result

    @staticmethod
    def _is_clear_quiet_zone(rows: tuple[str, ...], margin: int) -> bool:
        n = len(rows)
        for y, row in enumerate(rows):
            if y < margin or y >= n - margin:
                if "1" in row:
                    return False
            elif "1" in row[:margin] or "1" in row[n - margin:]:
                return False
        return True

    @staticmethod
    def _fixed_patterns_ok(rows: tuple[str, ...]) -> bool:
        n = len(rows)
        if not QrMatrixInspector._valid_dimension(n):
            return False
        # Localizadores: todos os 147 módulos dos três cantos.
        for x0, y0 in ((0, 0), (n - 7, 0), (0, n - 7)):
            for dy in range(7):
                for dx in range(7):
                    expected = "1" if (
                        dx in (0, 6) or dy in (0, 6)
                        or (2 <= dx <= 4 and 2 <= dy <= 4)
                    ) else "0"
                    if rows[y0 + dy][x0 + dx] != expected:
                        return False
        # Separadores do padrão: 45 módulos distintos.
        separators = set()
        for i in range(8):
            separators.update(((7, i), (i, 7), (n - 8, i), (n - 8 + i, 7),
                               (7, n - 8 + i), (i, n - 8)))
        if any(rows[y][x] != "0" for x, y in separators):
            return False
        for i in range(8, n - 8):
            expected = "1" if i % 2 == 0 else "0"
            if rows[6][i] != expected or rows[i][6] != expected:
                return False
        return True

    @staticmethod
    def _decode_qr(rows: tuple[str, ...]) -> str | None:
        """Decodifica em memória com ZXing; não registra nem executa o texto."""
        try:
            import zxingcpp
            from PIL import Image
        except ImportError:
            return None
        n = len(rows)
        side = n + 8  # quatro módulos de quiet zone ao rasterizar
        pixels = bytearray([255]) * (side * side)
        for y, row in enumerate(rows):
            for x, bit in enumerate(row):
                if bit == "1":
                    pixels[(y + 4) * side + x + 4] = 0
        image = Image.frombytes("L", (side, side), bytes(pixels)).convert("RGB")
        nearest = getattr(getattr(Image, "Resampling", Image), "NEAREST")
        for scale in (4, 8, 12):
            rendered = image.resize((side * scale, side * scale), resample=nearest)
            try:
                codes = zxingcpp.read_barcodes(rendered)
            except Exception:
                return None
            for code in codes:
                if "qr" not in str(getattr(code, "format", "")).casefold():
                    continue
                text = getattr(code, "text", None)
                if isinstance(text, str) and text:
                    return text
        return None
