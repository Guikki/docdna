"""CF-QA 003.9.5 — validação conservadora de matriz QR Code Model 2.

Inspeciona sequências 0/1 representadas por trechos nativos de PDF.
Não lê PDFs, não interpreta payload, não executa conteúdo e não conclui
ocultação, fraude ou Prompt Injection. Complementa QrStructuralInspector.

Aceita grupos gerados por QrStructuralInspector._group (chaves 'texts',
'span_count', 'page_number', 'font_name', 'bbox'), preservando os registros
já produzidos pelo pipeline existente.
"""
from __future__ import annotations

from hashlib import sha256
from math import isqrt
from typing import Any, Iterable


class QrMatrixInspector:
    """Reconstrói candidatos e valida padrões fixos do QR convencional."""

    MIN_SIZE = 21
    MAX_SIZE = 177
    MAX_BITS = MAX_SIZE * MAX_SIZE
    MAX_FRAGMENTS = 10000
    _FORMAT_POLY = 0x537
    _FORMAT_MASK = 0x5412
    _VERSION_POLY = 0x1F25

    def inspect_group(self, group: dict[str, Any]) -> dict[str, Any]:
        """Retorna diagnóstico estritamente estrutural sem divulgar os bits."""
        if not isinstance(group, dict):
            raise TypeError("group must be a dictionary")
        raw_fragments = group.get("texts", ())
        if not isinstance(raw_fragments, (tuple, list)):
            return self._result(group, "INVALID_FRAGMENTS", "texts não é uma lista/tupla")
        if len(raw_fragments) > self.MAX_FRAGMENTS:
            return self._result(group, "LIMIT_EXCEEDED", "fragmentos acima do limite")
        if group.get("truncated"):
            return self._result(group, "INCOMPLETE_CAPTURE", "grupo truncado na inspeção estrutural")

        fragments: list[str] = []
        for fragment in raw_fragments:
            if not isinstance(fragment, str):
                return self._result(group, "INVALID_FRAGMENTS", "fragmento não textual")
            if any(char not in "01 \t\r\n" for char in fragment):
                return self._result(group, "NOT_BINARY", "caracteres além de 0 e 1")
            bits = "".join(fragment.split())
            if bits:
                fragments.append(bits)

        raw_bits = "".join(fragments)
        length = len(raw_bits)
        result = self._result(group, "NOT_QR_MATRIX", "sem matriz QR comprovada")
        result.update({
            "bit_count": length,
            "fragment_count": len(fragments),
            "fragment_lengths": self._lengths(fragments),
            "raw_bits_sha256": sha256(raw_bits.encode("ascii")).hexdigest(),
        })

        if not raw_bits:
            result["reason"] = "sequência vazia"
            return result
        if length > self.MAX_BITS:
            result["status"] = "LIMIT_EXCEEDED"
            result["reason"] = "sequência acima do limite de módulos"
            return result

        n = isqrt(length)
        if n * n != length or not self._valid_dimension(n):
            result["reason"] = "total de bits não corresponde a uma dimensão QR Model 2"
            return result
        result["dimension"] = n
        result["version"] = (n - 17) // 4
        if len(fragments) == n and all(len(row) == n for row in fragments):
            rows = tuple(fragments)
            result["reconstruction_method"] = "one_fragment_per_row"
        else:
            # Uma fonte PDF pode agrupar a matriz inteira em um único span.
            # Isso é uma hipótese de ordem linear, sujeita à validação rigorosa.
            rows = tuple(raw_bits[i : i + n] for i in range(0, length, n))
            result["reconstruction_method"] = "row_major_stream_hypothesis"

        result["status"] = "QR_MATRIX_CANDIDATE_UNCONFIRMED"
        result["reason"] = "dimensão compatível; padrões estruturais ainda não validados"
        for orientation, inverted, candidate in self._orientations(rows):
            check = self._validate(candidate)
            if check is None:
                continue
            result.update({
                "status": "QR_MATRIX_STRUCTURALLY_VALIDATED",
                "reason": "padrões de posição, separação, sincronização, formato e versão coerentes",
                "orientation": orientation,
                "inverted": inverted,
                "mask_pattern": check["mask_pattern"],
                "error_correction_level": check["error_correction_level"],
                "matrix_structurally_validated": True,
            })
            return result
        return result

    @classmethod
    def normalized_rows(cls, group: dict[str, Any], finding: dict[str, Any]) -> tuple[str, ...] | None:
        """Reconstrói a variante aprovada, para decodificação OPCIONAL externa.

        Não transforma as sequências em comandos. Retorna apenas dados binários.
        """
        if finding.get("status") != "QR_MATRIX_STRUCTURALLY_VALIDATED":
            return None
        fragments = group.get("texts", ())
        if not isinstance(fragments, (tuple, list)) or any(not isinstance(f, str) for f in fragments):
            return None
        bits = "".join("".join(fragment.split()) for fragment in fragments)
        n = finding.get("dimension")
        if not isinstance(n, int) or len(bits) != n * n:
            return None
        rows = tuple(bits[i:i+n] for i in range(0, len(bits), n))
        for orientation, inverted, candidate in cls._orientations(rows):
            if orientation == finding.get("orientation") and inverted == finding.get("inverted"):
                return candidate
        return None

    @staticmethod
    def _lengths(fragments: Iterable[str]) -> dict[int, int]:
        histogram: dict[int, int] = {}
        for text in fragments:
            histogram[len(text)] = histogram.get(len(text), 0) + 1
        return dict(sorted(histogram.items()))

    @staticmethod
    def _result(group: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
        return {
            "status": status,
            "reason": reason,
            "page_number": group.get("page_number"),
            "font_name": group.get("font_name"),
            "bounding_box_pdf_points": group.get("bbox"),
            "bit_count": 0,
            "fragment_count": 0,
            "fragment_lengths": {},
            "raw_bits_sha256": None,
            "dimension": None,
            "version": None,
            "reconstruction_method": None,
            "orientation": None,
            "inverted": None,
            "mask_pattern": None,
            "error_correction_level": None,
            "matrix_structurally_validated": False,
            "payload_decoded": False,
            "payload_equal_to_visual_qr": None,
            "visually_concealed": None,
        }

    @classmethod
    def _valid_dimension(cls, n: int) -> bool:
        return cls.MIN_SIZE <= n <= cls.MAX_SIZE and (n - 17) % 4 == 0

    @staticmethod
    def _rotate(rows: tuple[str, ...]) -> tuple[str, ...]:
        n = len(rows)
        return tuple("".join(rows[n - 1 - x][y] for x in range(n)) for y in range(n))

    @classmethod
    def _orientations(cls, rows: tuple[str, ...]):
        for mirrored in (False, True):
            current = tuple(row[::-1] for row in rows) if mirrored else rows
            for turns in range(4):
                orientation = f"{'mirror_' if mirrored else ''}rotation_{turns * 90}"
                yield orientation, False, current
                yield orientation, True, tuple("".join("1" if b == "0" else "0" for b in row) for row in current)
                current = cls._rotate(current)

    @classmethod
    def _validate(cls, rows: tuple[str, ...]) -> dict[str, Any] | None:
        n = len(rows)
        if not cls._valid_dimension(n) or any(len(row) != n or any(c not in "01" for c in row) for row in rows):
            return None
        version = (n - 17) // 4
        for x0, y0 in ((0, 0), (n-7, 0), (0, n-7)):
            for dy in range(7):
                for dx in range(7):
                    expected = "1" if (dx in (0, 6) or dy in (0, 6) or (2 <= dx <= 4 and 2 <= dy <= 4)) else "0"
                    if rows[y0+dy][x0+dx] != expected:
                        return None
        # Separadores claros: retângulos de 8x8 ao redor dos localizadores.
        for x, y in (
            *((7, yy) for yy in range(8)),
            *((xx, 7) for xx in range(8)),
            *((n-8, yy) for yy in range(8)),
            *((xx, 7) for xx in range(n-8, n)),
            *((7, yy) for yy in range(n-8, n)),
            *((xx, n-8) for xx in range(8)),
        ):
            if rows[y][x] != "0":
                return None
        for index in range(8, n-8):
            expected = "1" if index % 2 == 0 else "0"
            if rows[6][index] != expected or rows[index][6] != expected:
                return None
        if rows[n-8][8] != "1":
            return None

        positions = cls._alignment_positions(version, n)
        for cy in positions:
            for cx in positions:
                if (cy == 6 and cx in (6, n-7)) or (cx == 6 and cy == n-7):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        expected = "1" if max(abs(dx), abs(dy)) in (0, 2) else "0"
                        if rows[cy+dy][cx+dx] != expected:
                            return None

        a = cls._format_value(rows, vertical=True)
        b = cls._format_value(rows, vertical=False)
        if a != b:
            return None
        payload = next((data for data in range(32) if cls._bch_format(data) == a), None)
        if payload is None:
            return None
        if version >= 7:
            expected_version = cls._bch_version(version)
            for i in range(18):
                bit = str((expected_version >> i) & 1)
                if rows[i//3][n-11+i%3] != bit or rows[n-11+i%3][i//3] != bit:
                    return None
        return {
            "mask_pattern": payload & 7,
            "error_correction_level": {0:"M", 1:"L", 2:"H", 3:"Q"}[payload >> 3],
        }

    @staticmethod
    def _alignment_positions(version: int, n: int) -> tuple[int, ...]:
        if version == 1:
            return ()
        count = version // 7 + 2
        step = 26 if version == 32 else ((version * 4 + count * 2 + 1) // (count * 2 - 2)) * 2
        return tuple([6] + [n - 7 - i * step for i in range(count - 2, -1, -1)])

    @staticmethod
    def _remainder(value: int, polynomial: int) -> int:
        while value.bit_length() >= polynomial.bit_length():
            value ^= polynomial << (value.bit_length() - polynomial.bit_length())
        return value

    @classmethod
    def _bch_format(cls, value: int) -> int:
        return ((value << 10) | cls._remainder(value << 10, cls._FORMAT_POLY)) ^ cls._FORMAT_MASK

    @classmethod
    def _bch_version(cls, version: int) -> int:
        return (version << 12) | cls._remainder(version << 12, cls._VERSION_POLY)

    @staticmethod
    def _format_value(rows: tuple[str, ...], *, vertical: bool) -> int:
        n = len(rows)
        value = 0
        for i in range(15):
            if vertical:
                x = 8
                y = i if i < 6 else i+1 if i < 8 else n-15+i
            else:
                y = 8
                x = n-i-1 if i < 8 else 15-i if i == 8 else 14-i
            if rows[y][x] == "1":
                value |= 1 << i
        return value
