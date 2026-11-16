from types import SimpleNamespace as NS

import pymupdf

from app.domain.readers.ocr_reader import OcrReader
from app.domain.services.document_identifier_service import DocumentIdentifierService


def _headers():
    return [NS(text=label, page_number=1, left=40+i*170, top=100,
               width=140, height=10, confidence=95)
            for i, label in enumerate(("Débito Automático", "Nº da Conta", "Nº da Fatura"))]


def test_regions_are_derived_from_multiple_unfilled_headers():
    [region] = DocumentIdentifierService().propose_ocr_regions(_headers(), [])
    assert region["page_number"] == 1
    assert set(region["missing_kinds"]) == {"automatic_debit", "account", "invoice"}
    x0, y0, x1, y1 = region["bounds_ocr_pixels"]
    assert x0 <= 40 and y0 <= 100 and x1 >= 520 and y1 > 110


def test_complete_headers_and_unlabelled_numbers_do_not_trigger_extra_ocr():
    fields = [{"kind": k, "page_number": 1} for k in ("automatic_debit", "account", "invoice")]
    assert DocumentIdentifierService().propose_ocr_regions(_headers(), fields) == []
    assert DocumentIdentifierService().propose_ocr_regions([
        NS(text="123456789012", page_number=1, left=40, top=100, width=140, height=10, confidence=95),
    ], []) == []


def test_headers_on_different_pages_are_not_combined():
    boxes = _headers()
    for i, box in enumerate(boxes):
        box.page_number = i + 1
    assert DocumentIdentifierService().propose_ocr_regions(boxes, []) == []


def test_region_ocr_transforms_coordinates_back_to_original_ocr_scale(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.pdf"
    with pymupdf.open() as doc:
        doc.new_page(width=200, height=300)
        doc.save(path)
    calls = []

    def ocr(image, **kwargs):
        calls.append(kwargs)
        return {"text": ["00001234567890"], "conf": [87],
                "left": [8], "top": [12], "width": [40], "height": [16]}

    monkeypatch.setattr("app.domain.readers.ocr_reader.pytesseract.image_to_data", ocr)
    [box] = OcrReader().read_regions(str(path), [{
        "page_number": 1, "bounds_ocr_pixels": (20, 40, 200, 100),
    }])
    assert (box.left, box.top, box.width, box.height) == (24, 46, 20, 8)
    assert box.confidence == 87
    assert box.page_number == 1
    assert calls[0]["config"] == "--psm 6"


def test_conflicting_region_reading_is_preserved_but_cannot_support_exact_match():
    field = {"kind": "automatic_debit", "label": "Débito automático", "value": "123456789019",
             "source": "OCR_REGION", "page_number": 1, "confidence": 92,
             "value_region": {"left": 100, "top": 200, "width": 110, "height": 12}}
    original = NS(text="123456789012", page_number=1, left=100, top=200,
                  width=110, height=12, confidence=29)
    service = DocumentIdentifierService()
    [annotated] = service.annotate_region_conflicts([field], [original])
    assert annotated["value"] == "123456789019"
    assert annotated["reading_conflict"] is True
    assert annotated["alternative_readings"][0]["value"] == "123456789012"
    assert service.compare([
        {"id": aid, "document_identifiers": [annotated]} for aid in ("a", "b")
    ]) == []


def test_rotated_page_does_not_receive_unverified_crop_coordinates(tmp_path, monkeypatch):
    path = tmp_path / "rotated.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page(width=200, height=300)
        page.set_rotation(90)
        doc.save(path)

    def forbidden(*args, **kwargs):
        raise AssertionError("OCR do recorte não deve presumir coordenadas não transformadas")

    monkeypatch.setattr("app.domain.readers.ocr_reader.pytesseract.image_to_data", forbidden)
    assert OcrReader().read_regions(str(path), [{
        "page_number": 1, "bounds_ocr_pixels": (20, 40, 200, 100),
    }]) == []
