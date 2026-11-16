"""CF-QA 003.4 — regressão do leitor de barcodes (sem simular fraude).

Os resultados ZXing são simulados; as transformações, a geometria,
PDF/PyMuPDF, deduplicação e os objetos de domínio são os reais.
"""

from __future__ import annotations

from types import SimpleNamespace

import pymupdf
import pytest
from PIL import Image

from app.domain.readers import barcode_reader as module
from app.domain.readers.barcode_reader import BarcodeReader, _ScanView


FULL_ITF = "84680000006096900481000112943786092506903643"


def _result(text="00104360", fmt="ITF", bounds=(90, 80, 300, 130)):
    left, top, right, bottom = bounds
    point = lambda x, y: SimpleNamespace(x=x, y=y)
    return SimpleNamespace(
        text=text,
        format=fmt,
        position=SimpleNamespace(
            top_left=point(left, top),
            top_right=point(right, top),
            bottom_right=point(right, bottom),
            bottom_left=point(left, bottom),
        ),
        orientation=0,
        ec_level=None,
        content_type=None,
    )


def _pdf(tmp_path, *, pages=1):
    path = tmp_path / "fatura_teste.pdf"
    with pymupdf.open() as document:
        for _ in range(pages):
            document.new_page(width=200, height=300)
        document.save(path)
    return str(path)


def _fake_reads(monkeypatch, fn):
    monkeypatch.setattr(module.zxingcpp, "read_barcodes", fn)


def test_original_preservado_e_sem_fallback_quando_itf_44_encontrado(tmp_path, monkeypatch):
    calls = []

    def decode(image):
        calls.append(image.size)
        return [_result(FULL_ITF)]

    _fake_reads(monkeypatch, decode)
    readings = BarcodeReader().read(_pdf(tmp_path))
    assert len(calls) == 1
    assert len(readings) == 1
    assert readings[0].content == FULL_ITF
    assert readings[0].page_number == 1
    assert readings[0].image_hash and len(readings[0].image_hash) == 64


def test_itf_curto_original_e_preservado_mesmo_sem_corroboração(tmp_path, monkeypatch):
    calls = 0

    def decode(image):
        nonlocal calls
        calls += 1
        return [_result()] if calls == 1 else []

    _fake_reads(monkeypatch, decode)
    readings = BarcodeReader().read(_pdf(tmp_path))
    assert [item.content for item in readings] == ["00104360"]
    assert calls > 1


def test_itf_44_recuperado_no_recorte_inferior_com_posicao_pdf_correta(tmp_path, monkeypatch):
    calls = 0

    def decode(image):
        nonlocal calls
        calls += 1
        if calls == 1:
            return [_result("00104360", bounds=(30, 80, 60, 150))]
        if calls == 5:  # original, contraste, reduzida, superior, inferior
            return [_result(FULL_ITF, bounds=(90, 100, 420, 140))]
        return []

    _fake_reads(monkeypatch, decode)
    readings = BarcodeReader().read(_pdf(tmp_path))
    assert len(readings) == 2
    recovered = next(item for item in readings if item.content == FULL_ITF)
    assert recovered.barcode_index == 2
    assert recovered.location.page_number == 1
    bbox = recovered.location.bounding_box
    assert bbox.x == pytest.approx(30)
    assert bbox.y == pytest.approx((360 + 100) / 3)
    assert bbox.width == pytest.approx(110)
    assert bbox.height == pytest.approx(40 / 3)
    assert recovered.image_hash and len(recovered.image_hash) == 64


def test_mesmo_codigo_em_duas_regioes_gera_duas_ocorrencias(tmp_path, monkeypatch):
    def decode(image):
        return [
            _result(FULL_ITF, bounds=(30, 30, 200, 90)),
            _result(FULL_ITF, bounds=(30, 600, 200, 660)),
        ]

    _fake_reads(monkeypatch, decode)
    results = BarcodeReader().read(_pdf(tmp_path))
    assert len(results) == 2
    assert results[0].location.bounding_box.y != results[1].location.bounding_box.y
    assert [item.barcode_index for item in results] == [1, 2]


def test_mesma_leitura_em_passagens_distintas_nao_gera_duplicidade(tmp_path, monkeypatch):
    calls = 0

    def decode(image):
        nonlocal calls
        calls += 1
        if calls in (1, 2):
            return [_result("00104360", bounds=(60, 80, 350, 130))]
        return []

    _fake_reads(monkeypatch, decode)
    results = BarcodeReader().read(_pdf(tmp_path))
    assert [item.content for item in results] == ["00104360"]


def test_itf_curto_encontrado_apenas_em_uma_tentativa_nova_nao_e_promovido(tmp_path, monkeypatch):
    calls = 0

    def decode(image):
        nonlocal calls
        calls += 1
        if calls == 2:
            return [_result("12345678")]
        return []

    _fake_reads(monkeypatch, decode)
    assert BarcodeReader().read(_pdf(tmp_path)) == []


def test_itf_curto_novo_exige_corroboração_em_duas_passagens(tmp_path, monkeypatch):
    calls = 0

    def decode(image):
        nonlocal calls
        calls += 1
        if calls == 2:
            return [_result("12345678", bounds=(100, 90, 300, 140))]
        if calls == 3:
            return [_result("12345678", bounds=(70, 63, 210, 98))]
        return []

    _fake_reads(monkeypatch, decode)
    readings = BarcodeReader().read(_pdf(tmp_path))
    assert len(readings) == 1
    assert readings[0].content == "12345678"
    assert readings[0].location.bounding_box.x == pytest.approx(100 / 3)


def test_qrcode_preservado_com_conteudo_e_hash(tmp_path, monkeypatch):
    calls = 0

    def decode(image):
        nonlocal calls
        calls += 1
        return [_result("pix-copia-e-cola", fmt="QRCode")] if calls == 1 else []

    _fake_reads(monkeypatch, decode)
    readings = BarcodeReader().read(_pdf(tmp_path))
    assert len(readings) == 1
    assert readings[0].content == "pix-copia-e-cola"
    assert readings[0].format == "QRCode"
    assert readings[0].image_hash is not None


def test_nao_inventa_codigo_se_nenhuma_passagem_decodificou(tmp_path, monkeypatch):
    _fake_reads(monkeypatch, lambda image: [])
    assert BarcodeReader().read(_pdf(tmp_path)) == []


def test_paginas_sao_distintas_e_indice_e_global(tmp_path, monkeypatch):
    _fake_reads(monkeypatch, lambda image: [_result(FULL_ITF)])
    result = BarcodeReader().read(_pdf(tmp_path, pages=2))
    assert [(x.page_number, x.barcode_index) for x in result] == [(1, 1), (2, 2)]


def test_rotacao_90_mapeia_posicao_para_pagina_original():
    image = Image.new("RGB", (900, 270), "white")
    try:
        view = _ScanView(image, (0, 0, 270, 900), (270, 900), 90, "esquerda")
        assert view.map_bounds((200, 150, 300, 210)) == pytest.approx((60, 200, 120, 300))
    finally:
        image.close()


def test_rotacao_270_mapeia_posicao_para_pagina_original():
    image = Image.new("RGB", (900, 270), "white")
    try:
        view = _ScanView(image, (330, 0, 600, 900), (270, 900), 270, "direita")
        assert view.map_bounds((600, 30, 700, 90)) == pytest.approx((360, 200, 420, 300))
    finally:
        image.close()


def test_regiao_redimensionada_volta_a_escala_original():
    image = Image.new("RGB", (420, 630), "white")
    try:
        view = _ScanView(image, (0, 0, 600, 900), image.size, 0, "reduzida")
        assert view.map_bounds((70, 140, 210, 210)) == pytest.approx((100, 200, 300, 300))
    finally:
        image.close()


def test_excecao_em_uma_variacao_nao_descarta_a_leitura_original(tmp_path, monkeypatch):
    calls = 0

    def decode(image):
        nonlocal calls
        calls += 1
        if calls == 1:
            return [_result("00104360")]
        if calls == 2:
            raise RuntimeError("falha de imagem derivada")
        return []

    _fake_reads(monkeypatch, decode)
    assert [x.content for x in BarcodeReader().read(_pdf(tmp_path))] == ["00104360"]


def test_falha_na_leitura_original_nao_fica_oculta(tmp_path, monkeypatch):
    def decode(image):
        raise RuntimeError("leitor indisponível")

    _fake_reads(monkeypatch, decode)
    with pytest.raises(RuntimeError, match="leitor indisponível"):
        BarcodeReader().read(_pdf(tmp_path))


def test_barcode_sem_posicao_continua_preservado(tmp_path, monkeypatch):
    no_position = _result(FULL_ITF)
    no_position.position = None
    _fake_reads(monkeypatch, lambda image: [no_position])
    read = BarcodeReader().read(_pdf(tmp_path))
    assert len(read) == 1
    assert read[0].location is None
    assert read[0].image_hash is None


def test_ha_dois_itfs_distintos_em_recortes_diferentes(tmp_path, monkeypatch):
    """Encontrar um ITF no primeiro recorte não interrompe os demais."""
    calls = 0
    second = "8" + "1" * 43

    def decode(image):
        nonlocal calls
        calls += 1
        if calls == 4:  # recorte superior
            return [_result(FULL_ITF, bounds=(40, 35, 350, 85))]
        if calls == 5:  # recorte inferior
            return [_result(second, bounds=(40, 360, 350, 400))]
        return []

    _fake_reads(monkeypatch, decode)
    result = BarcodeReader().read(_pdf(tmp_path))
    assert {item.content for item in result} == {FULL_ITF, second}
    assert len(result) == 2


def test_leitura_nova_sem_posicao_exige_duas_passagens(tmp_path, monkeypatch):
    calls = 0

    def decode(image):
        nonlocal calls
        calls += 1
        if calls == 2:
            item = _result(FULL_ITF)
            item.position = None
            return [item]
        return []

    _fake_reads(monkeypatch, decode)
    assert BarcodeReader().read(_pdf(tmp_path)) == []
