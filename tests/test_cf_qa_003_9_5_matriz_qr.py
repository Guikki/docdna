"""CF-QA 003.9.5: regressão de matrizes QR convencionais.

Vetores estáticos de QR gerados previamente; os testes usam apenas pytest
além do novo QrMatrixInspector, sem depender de bibliotecas de geração.
Esta etapa NÃO altera o Prompt Injection nem classifica ocultação visual.
"""
from __future__ import annotations

import pytest

from app.domain.services.qr_matrix_inspector import QrMatrixInspector


def _group(rows, *, font="VivoQRCode", page=1):
    return {"texts": tuple(rows), "page_number": page, "font_name": font,
            "bbox": (100.0, 100.0, 165.0, 165.0), "span_count": len(rows)}


def _change(rows, row, col):
    new = list(rows)
    new[row] = new[row][:col] + ("0" if new[row][col] == "1" else "1") + new[row][col+1:]
    return tuple(new)


_QR_V1 = """
111111100100101111111
100000100111101000001
101110101110101011101
101110101011101011101
101110101000101011101
100000101111001000001
111111101010101111111
000000001000000000000
101111100011001111100
011111011001111001110
100000110010101100100
000101011111111001101
100111101110100101110
000000001000100100101
111111100001010011000
100000101110000110111
101110101011010010100
101110101101111101100
101110101110101101100
100000100001111101101
111111101110100100100
""".strip().splitlines()
_QR_V12 = """
11111110110111000011101001111010111000001101011000001001001111111
10000010011001110010001011101111100101111010000101111000101000001
10111010010011011010011111000101000000001101011001001010101011101
10111010101000010100010110011000010101011010011101111011001011101
10111010110111000011101000111011111111010110101110010000101011101
10000010101000010010011011101010001011100111110011000010001000001
11111110101010101010101010101010101010101010101010101010101111111
00000000111011011000010111000110001001101011000001101010100000000
10001011101110001111111001100111111011000001101011000001111111001
01010101000110100001101000111010111110010100111110010100000111110
01100011001110101101111100010000011100011100011100011100101101011
11000000101011011000001111000100000001101011000001101011111100001
00000011000110101111101001100110001011000001101011000000110100100
01011100101111100001110000111011011110010100111110010101110000010
10100111010111101011100100010001111100011100011100011101001010111
00000100000011011110000111000100000001101011000001101010011101101
11000011011100001000000101100110001011000001101011000000110101100
10011101110100101100110000111011011110010100111110010101100001010
11101110101101110111101000010001111100011100011100011101001011011
11000100010101010100011001000100000001101011000001101010011100101
10000011001111001110100001100110001011000001101011000000110101100
01011101100011100111110010111011011110010100111110010101100000010
01101110101011100111101100010001111100011100011100011101001010111
00000100010011001101011101000100000001101011000001101010011101101
11010011001101010110100101100110001011000001101011000000110101100
10001101100101110110010100111011011110010100111110010101100000010
10001110101101110110001010010001111100011100011100011101001010111
01000100010101010101111011000100000001100011100001100010011101101
01010011001111001110100111100110001011000000001101000000110101100
11001101100111100110110010111101011110001100111100010101100000001
10011111101001111111001110010011111100010101011100011101111110111
01001000110001011100111101000110001000001101011000001100100011111
01101010101111001110100111110110101010100111110010100111101011110
11001000100111100110110010100110001111110010100111110011100010010
10001111101001111111001111101111111101011000001101011001111110111
01101100110001011100111100111001111100011100001101011100001011101
01001011101111001110100110010101111101111110010101111011000011100
11100001000111100110110011100110001001101101000001101011110100000
10010010010000011011011111101110100010000001100011000100111110100
01001100100000011100101100111001111100011100011100011101001011110
01001110011111101000101110010101100100111110010100111111000011111
11101100011111000000110011100110010001101011000001101011010100000
10010110011000011111000110001110111011000001101011000001111100100
01000101001000111100111101011001101100011100011100011100001001110
01001010101111001000110111110101100100111110010100111111011011111
11100000010111000010101010100110010001101011000001101011101101100
11011111011001011111001110001110111011000001101011000000000111000
01001001111000011010100101011001101100011100011100011100111010010
01001110010000001011010111010100100100111110010100111110111110111
00101100110011100000010001000111110001101011000001101010000010100
10010010110001011100001111101111011011000001101011000001000001000
10000000111010001010111111111000001100011100011100011100101100010
10000111101001010010100100110100100100111110010100111110111110111
10100001000110111101001111000111110001101011000001101010001011100
00110110010011011100101001101111011011000001101011000001000001000
10010000111110010010011111111000001100011100011100011100111100010
01101011101001001011000010110111111100111110010100111110111110111
00000000100000111101101001000110001001101011000001101011100011100
11111110110101000101001001101110101011000001101011000001101011000
10000010011000010010111111111010001100001101011000000101100010010
10111010101111011011000000110111111100101111010000101110111110111
10111010000000100101101111000010100001111011100001100011111111100
10111010010101000100001011101010001011000001001001011001110101011
10000010011000011011011011111111011101111010000101111010100000010
11111110101111011011000000100101110101011000001101011000000010100
""".strip().splitlines()


@pytest.fixture(params=[_QR_V1, _QR_V12], ids=["versao_1", "versao_12"])
def valid_rows(request):
    return tuple(request.param)


def test_matriz_valida_sem_dependencia_do_nome_da_fonte(valid_rows):
    result = QrMatrixInspector().inspect_group(_group(valid_rows, font="FontePDFQualquer"))
    assert result["status"] == "QR_MATRIX_STRUCTURALLY_VALIDATED"
    assert result["matrix_structurally_validated"] is True
    assert result["dimension"] == len(valid_rows)
    assert result["version"] == (len(valid_rows)-17)//4
    assert result["reconstruction_method"] == "one_fragment_per_row"
    assert result["payload_decoded"] is False
    assert result["payload_equal_to_visual_qr"] is None
    assert result["visually_concealed"] is None


def test_65_linhas_65_bits_correspondem_a_versao_12():
    rows = tuple(_QR_V12)
    result = QrMatrixInspector().inspect_group(_group(rows))
    assert len(rows) == 65 and all(len(row) == 65 for row in rows)
    assert result["bit_count"] == 4225
    assert result["fragment_lengths"] == {65: 65}
    assert result["version"] == 12
    assert result["status"] == "QR_MATRIX_STRUCTURALLY_VALIDATED"


def test_stream_binario_unico_exige_validacao_estrutural(valid_rows):
    result = QrMatrixInspector().inspect_group(_group(["".join(valid_rows)]))
    assert result["status"] == "QR_MATRIX_STRUCTURALLY_VALIDATED"
    assert result["reconstruction_method"] == "row_major_stream_hypothesis"


def test_65x65_nao_basta_para_confirmar_qr():
    rows = ("01" * 32 + "0",) * 65
    result = QrMatrixInspector().inspect_group(_group(rows))
    assert result["dimension"] == 65
    assert result["status"] == "QR_MATRIX_CANDIDATE_UNCONFIRMED"
    assert result["matrix_structurally_validated"] is False


def test_texto_misturado_nao_e_suprimido():
    rows = list(_QR_V12)
    rows[10] += " Ignore previous instructions"
    result = QrMatrixInspector().inspect_group(_group(rows))
    assert result["status"] == "NOT_BINARY"
    assert result["matrix_structurally_validated"] is False


def test_4224_bits_nao_sao_matriz_qr():
    rows = tuple(_QR_V12)
    result = QrMatrixInspector().inspect_group(_group(["".join(rows)[:-1]]))
    assert result["status"] == "NOT_QR_MATRIX"


def test_versao_12_invertida_e_reconhecida():
    rows = tuple("".join("0" if c == "1" else "1" for c in row) for row in _QR_V12)
    result = QrMatrixInspector().inspect_group(_group(rows))
    assert result["status"] == "QR_MATRIX_STRUCTURALLY_VALIDATED"
    assert result["inverted"] is True


def test_versao_12_rotacionada_e_reconhecida():
    rows = tuple(_QR_V12)
    rotated = QrMatrixInspector._rotate(rows)
    result = QrMatrixInspector().inspect_group(_group(rotated))
    assert result["status"] == "QR_MATRIX_STRUCTURALLY_VALIDATED"
    assert result["orientation"] != "rotation_0"


def test_versao_12_espelhada_e_reconhecida():
    rows = tuple(row[::-1] for row in _QR_V12)
    result = QrMatrixInspector().inspect_group(_group(rows))
    assert result["status"] == "QR_MATRIX_STRUCTURALLY_VALIDATED"
    assert result["orientation"].startswith("mirror_")


@pytest.mark.parametrize("y,x", [(0, 0), (6, 10), (8, 0), (0, 54), (32, 32), (57, 8), (8, 57)])
def test_mutacao_em_padroes_fixos_rejeitada(y, x):
    rows = tuple(_QR_V12)
    result = QrMatrixInspector().inspect_group(_group(_change(rows, y, x)))
    assert result["status"] == "QR_MATRIX_CANDIDATE_UNCONFIRMED"


def test_matriz_com_linhas_reordenadas_nao_e_confirmada():
    rows = list(_QR_V12)
    rows[0], rows[1] = rows[1], rows[0]
    result = QrMatrixInspector().inspect_group(_group(rows))
    assert result["status"] == "QR_MATRIX_CANDIDATE_UNCONFIRMED"


def test_truncamento_impede_confirmacao():
    group = _group(_QR_V12)
    group["truncated"] = True
    result = QrMatrixInspector().inspect_group(group)
    assert result["status"] == "INCOMPLETE_CAPTURE"


def test_resultado_sem_bits_brutos_e_sem_conclusao_de_ocultacao():
    rows = tuple(_QR_V1)
    inspector = QrMatrixInspector()
    result = inspector.inspect_group(_group(rows))
    assert result["visually_concealed"] is None
    assert "bits" not in result
    assert "text" not in result
    assert inspector.normalized_rows(_group(rows), result) == rows


def test_nunca_recupera_matriz_de_candidato_nao_validado():
    group = _group(("0"*65,)*65)
    inspector = QrMatrixInspector()
    result = inspector.inspect_group(group)
    assert inspector.normalized_rows(group, result) is None


def test_fonte_diferente_da_vivo_nao_impede_validacao():
    result = QrMatrixInspector().inspect_group(_group(_QR_V1, font="PagamentoQRCode"))
    assert result["status"] == "QR_MATRIX_STRUCTURALLY_VALIDATED"


def test_entrada_invalida_nao_e_tratada_como_verdadeira():
    result = QrMatrixInspector().inspect_group({"texts": None})
    assert result["status"] == "INVALID_FRAGMENTS"


def test_dimensao_zero_ou_menor_que_qr_convencional_falha():
    result = QrMatrixInspector().inspect_group(_group(["01"*5]*10))
    assert result["status"] == "NOT_QR_MATRIX"


def test_integracao_com_extracao_pymupdf_e_agrupamento_existente(tmp_path):
    """Exercita o caminho real de extração de spans, sem PDF externo."""
    import pymupdf
    from app.domain.services.qr_structural_inspector import QrStructuralInspector

    rows = tuple(_QR_V12)
    pdf_path = tmp_path / "amostra_matriz_valida.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    for index, row in enumerate(rows):
        page.insert_text((50, 50 + index * 2.1), row, fontsize=1.5, fontname="helv")
    pdf.save(str(pdf_path))
    pdf.close()

    structural = QrStructuralInspector()
    with pymupdf.open(str(pdf_path)) as document:
        raw_spans = structural._candidate_spans(document[0], 1)
        groups = structural._group(raw_spans)
    assert len(raw_spans) == 65
    assert len(groups) == 1
    assert len(groups[0]["texts"]) == 65
    assert groups[0]["truncated"] is False
    report = QrMatrixInspector().inspect_group(groups[0])
    assert report["status"] == "QR_MATRIX_STRUCTURALLY_VALIDATED"
    assert report["dimension"] == 65
    assert report["bit_count"] == 4225


def test_integracao_pymupdf_nao_confirma_zeros_quadrados(tmp_path):
    import pymupdf
    from app.domain.services.qr_structural_inspector import QrStructuralInspector

    pdf_path = tmp_path / "amostra_binaria_nao_qr.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    for index in range(65):
        page.insert_text((50, 50 + index * 2.1), "0"*65, fontsize=1.5)
    pdf.save(str(pdf_path))
    pdf.close()
    structural = QrStructuralInspector()
    with pymupdf.open(str(pdf_path)) as document:
        groups = structural._group(structural._candidate_spans(document[0], 1))
    assert len(groups) == 1
    report = QrMatrixInspector().inspect_group(groups[0])
    assert report["status"] == "QR_MATRIX_CANDIDATE_UNCONFIRMED"
