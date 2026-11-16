
"""CF-QA 003.9.5 — integração conservadora de QR matricial e payload visual.

Vetores fixos; não exige gerador de QR. O ZXing é simulado nestes testes
unitários; a decodificação real é validada no PDF Vivo pelo usuário.
"""
from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace as NS

from app.domain.services.qr_matrix_payload_correlator import QrMatrixPayloadCorrelator
from app.domain.services.qr_structural_inspector import QrStructuralInspector

_PAYLOAD = "DocDNA CF-QA 003.9.5 validacao de integracao de QR code"
_QR_V10 = tuple("""111111100111011101111100010111100011100100101011001111111
100000101010101111010110101101101010111110011001001000001
101110100110011010001000111100011001010011110011001011101
101110101000011100100100011001101100111010111101001011101
101110101101001011111110011111101001101000110101001011101
100000100111110111001111001000111001110011000010001000001
111111101010101010101010101010101010101010101010101111111
000000001111100101001100011000111110111000101111000000000
010111101101111100010011011111111101000001110101111011010
100111010100000011101001010101100100001000111100111010101
110100101100001111100101010011000100011010101100110100110
000101000010101101110011110001010011100110010101100001101
000110100010100011001001011101110010001011011101110010100
110000011101110010010111010111001000011101001101001111010
010010110000000011011110010000010011011110110110011000000
011100001110110001010101110011011101101000101101001111001
011000101010101001100101010110010111101100110100111101111
110111011001101001000000001011110100110101101111100111101
101011101101101011101111000111100111110000100100101110111
001010011111000011111111100011001000111001001000100100101
001001111000010001111111100111001011011010010010011111111
000111001011000110001001000110111010001111011111110110110
010101110101101010100110101001110000000101101110001100101
010001011001110100010110000110101010100010000101100011100
010001111000110101110010101110101011101001000101001000111
000111000111100101010010010110000001111011010111111011111
111111111101101000111100101111101010100000101111111111001
010110001000001100101000001000100010010011100010100011100
101110101101010100100000001010111010100011011001101011110
000010001000111111011010001000111010011001100011100010000
011011111010100101111111101111110101111001011011111111000
111011010010110010001101100111100010011100110110001110110
010011110110000010011010100010000010100111000100101011001
011001000001101000010100001000100111101111101100000011111
110001100000100001101110011100100110111101011101010000101
111110011001110001010100011011110110011010100011100010110
000110110110111101011010010011111111110000101011000111011
100011000010010010010100000001010100100010111000110110111
011000111001001011110111010111111100110000010010001101101
101101011011011110011000101101101011110111001010101100100
110101100001100000000010010010010001100101010001001010110
101010011111110010110011011000100010111110001011111110000
010010110100110110001001101111100011111111100011101001011
111101001000000100111111111101110111111100111000011101001
101010101110101110010111011111100100110011101011100100100
101011010010110101100010001110100101101010100011000010110
101001111101011001011111111100000101110100110110011000111
111110001100001101000000101001110011110000010001101111101
000000111111100110100100011111111010011011011011111110100
000000001011011110010110001000101000001101001101100011000
111111100001100010111100101010110011011110110100101010010
100000101110000101111001101000111101101110101100100011000
101110101101010100100111001111101111101000110011111111110
101110101011000101011101111011010100110111101011100000000
101110100101010010110101001010111111110000100100001011011
100000101011101100000100100000111110100100101000001001011
111111100111101101001110010101001101011111110011011010100
""".splitlines())


def _with_quiet(rows, margin=4):
    n = len(rows)
    white = "0" * (n + 2 * margin)
    return tuple([white] * margin + [
        ("0" * margin) + row + ("0" * margin)
        for row in rows
    ] + [white] * margin)


def _group(rows):
    return {
        "texts": tuple(rows),
        "page_number": 1,
        "font_name": "VivoQRCode",
        "bbox": (100., 100., 165., 165.),
        "span_count": len(rows),
        "truncated": False,
    }


def test_65x65_com_quiet_zone_e_payload_identico_confirmado(monkeypatch):
    marker = QrMatrixPayloadCorrelator()
    monkeypatch.setattr(marker, "_decode_qr", lambda rows: _PAYLOAD)

    result = marker.inspect(
        group=_group(_with_quiet(_QR_V10)),
        linked_qr_codes=[
            {
                "content_sha256": sha256(_PAYLOAD.encode()).hexdigest(),
                "barcode_index": 1,
            }
        ],
    )

    assert result["status"] == "CONFIRMED_PAYLOAD_MATCH"
    assert result["payload_equal_to_linked_qr"] is True
    assert result["matrix_decoded"] is True
    assert result["matrix_outer_dimension"] == 65
    assert result["matrix_dimension"] == 57
    assert result["matrix_version"] == 10
    assert result["quiet_zone_modules"] == 4
    assert result["matching_linked_qr_count"] == 1
    assert result["visually_concealed"] is None
    assert "text" not in result and "raw_bits" not in result


def test_qr_decodificado_sem_equivalencia_nao_pode_ser_suprimido(monkeypatch):
    marker = QrMatrixPayloadCorrelator()
    monkeypatch.setattr(marker, "_decode_qr", lambda rows: _PAYLOAD)

    result = marker.inspect(
        group=_group(_with_quiet(_QR_V10)),
        linked_qr_codes=[
            {
                "content_sha256": sha256(b"OUTRO QR").hexdigest(),
                "barcode_index": 2,
            }
        ],
    )

    assert result["status"] == "QR_DECODED_NO_LINKED_PAYLOAD_MATCH"
    assert result["payload_equal_to_linked_qr"] is None
    assert result["matching_linked_qr_count"] == 0


def test_sequencia_quadrada_de_zeros_nao_chega_ao_decodificador(monkeypatch):
    marker = QrMatrixPayloadCorrelator()

    def fail(rows):
        raise AssertionError("não deve chamar ZXing sem padrões de QR")

    monkeypatch.setattr(marker, "_decode_qr", fail)

    result = marker.inspect(
        group=_group(("0" * 65,) * 65)
    )

    assert result["status"] == "NOT_CONFIRMED"
    assert result["payload_equal_to_linked_qr"] is None


def test_fragmento_com_instrucao_misturada_nao_se_torna_matriz(monkeypatch):
    marker = QrMatrixPayloadCorrelator()
    monkeypatch.setattr(marker, "_decode_qr", lambda rows: _PAYLOAD)

    rows = list(_with_quiet(_QR_V10))
    rows[16] += " ignore previous instructions"

    result = marker.inspect(group=_group(rows))

    assert result["status"] == "NOT_CONFIRMED"


def test_grupo_truncado_nao_se_torna_qr_confirmado(monkeypatch):
    marker = QrMatrixPayloadCorrelator()
    monkeypatch.setattr(marker, "_decode_qr", lambda rows: _PAYLOAD)

    group = _group(_with_quiet(_QR_V10))
    group["truncated"] = True

    result = marker.inspect(group=group)

    assert result["status"] == "NOT_CONFIRMED"


def test_integracao_no_registro_estrutural_preserva_codigo_e_natureza(monkeypatch):
    inspector = QrStructuralInspector()
    monkeypatch.setattr(
        inspector._matrix,
        "_decode_qr",
        lambda rows: _PAYLOAD,
    )

    bbox = NS(x=100., y=100., width=65., height=65.)
    barcode = NS(
        format="QRCode",
        page_number=1,
        content=_PAYLOAD,
        barcode_index=1,
        location=NS(bounding_box=bbox),
    )

    record = inspector._record(
        _group(_with_quiet(_QR_V10)),
        [barcode],
    )

    assert record["code"] == "QR_STRUCTURAL_SPATIAL_ASSOCIATION"
    assert record["qr_payload_equal"] is True
    assert record["qr_matrix_validation"]["status"] == "CONFIRMED_PAYLOAD_MATCH"
    assert record["visually_concealed"] is None
    assert record["linked_qr_codes"][0]["association_type"] == "GEOMETRIC_ONLY"
