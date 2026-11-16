from types import SimpleNamespace as NS

import pytest

from app.domain.readers.printed_numeric_line_reader import PrintedNumericLineReader
from app.domain.services.document_identifier_service import DocumentIdentifierService
from app.domain.rules.numeric_line_validator import NumericLineValidator
from app.domain.models.printed_numeric_line import PrintedNumericLine
from app.domain.comparators.duplicate_itf_different_numeric_line_comparator import DuplicateItfDifferentNumericLineComparator
from app.domain.services.numeric_line_forensic_element_adapter import NumericLineForensicElementAdapter
from app.domain.services.barcode_numeric_line_candidate_selector import BarcodeNumericLineCandidateSelector
from app.domain.services.forensic_element_catalog import ForensicElementCatalog
from uuid import uuid4


def _box(text, x, y, *, page=1):
    return NS(text=text, left=x, top=y, width=110, height=12,
              page_number=page, confidence=95)


def _read(boxes, text):
    return PrintedNumericLineReader().read(
        NS(content=""), NS(content=text), ocr_text_boxes=boxes,
    )


@pytest.mark.parametrize("values,labels", [
    (("123456789012", "00001234567890", "00009876543210"),
     ("Débito Automático", "Nº da Conta", "Nº da Fatura")),
    (("812345678901", "234567890123", "345678901234", "456789012345"),
     ("Débito Automático", "Nº da Conta", "Nº da Fatura", "Código Cliente")),
])
def test_labeled_cells_are_preserved_as_observation_but_not_payment_candidate(values, labels):
    boxes = [
        _box(label, 100 + i * 160, 100)
        for i, label in enumerate(labels)
    ] + [_box(value, 100 + i * 160, 125) for i, value in enumerate(values)]
    [line] = _read(boxes, " ".join(values))
    assert line.normalized_content == "".join(values)
    assert line.raw_content == " ".join(values)
    assert getattr(line, "contextual_kind", "unclassified") == "concatenated_fields"
    assert line.contextual_metadata["page_number"] == 1
    assert len({f["kind"] for f in line.contextual_metadata["fields"]}) == len(values)
    assert NumericLineValidator().validate(line).status.value == "inconclusive"


@pytest.mark.parametrize("mode", ["no_labels", "different_pages", "different_rows", "rotated"])
def test_numeric_groups_without_unambiguous_field_geometry_remain_candidates(mode):
    values = ("123456789012", "234567890123", "345678901234", "456789012345")
    boxes = [_box(v, 100 + i * 160, 125, page=(i + 1 if mode == "different_pages" else 1))
             for i, v in enumerate(values)]
    if mode != "no_labels":
        boxes += [_box("Nº da Conta", 100, 100),
                  _box("Nº da Fatura", 260, 25 if mode == "different_rows" else 100)]
    if mode == "rotated":
        for box in boxes:
            box.left, box.top = box.top, box.left
    lines = _read(boxes, " ".join(values))
    assert all(getattr(line, "contextual_kind", "unclassified") != "concatenated_fields"
               for line in lines)


def test_stacked_identifier_exposes_value_region_separately_from_label():
    [item] = DocumentIdentifierService().extract(ocr_text_boxes=[
        _box("Nº da Fatura", 100, 100), _box("00001234567890", 100, 125),
    ])
    assert item["value_region"] == {"left": 100.0, "top": 125.0,
                                    "width": 110.0, "height": 12.0}
    assert item["coordinate_system"] == "ocr_pixels"


def test_proven_fields_do_not_enter_payment_validation_or_either_comparison_path():
    line = PrintedNumericLine(1, "ocr", "8" * 48, "8" * 48, 48,
                              contextual_kind="concatenated_fields")
    validation = NumericLineValidator().validate(line)
    assert validation.status.value == "inconclusive"
    assert validation.validation_method is None
    assert "posicional" in validation.message
    comparator = DuplicateItfDifferentNumericLineComparator()
    assert comparator._extract_numeric_lines({"printed_numeric_lines": [line]}) == []
    aid = uuid4()
    elements = NumericLineForensicElementAdapter().build(
        document_id=aid, lines=[line], validations=[validation],
    )
    catalog = ForensicElementCatalog()
    for element in elements:
        catalog.add(element)
    assert any(e.value == line.raw_content for e in elements)
    assert BarcodeNumericLineCandidateSelector()._numeric_lines_for_document(
        catalog=catalog, document_id=aid,
    ) == ((), ())


def test_native_stacked_fields_reuse_existing_extractor_and_preserve_pdf_coordinates():
    def span(text, x, y):
        return NS(text=text, page_number=2,
                  bounding_box=NS(left=x, top=y, right=x + 100, bottom=y + 10))
    document = NS(pages=[NS(number=2, text_spans=[
        span("Débito Automático", 50, 100), span("Nº da Fatura", 220, 100),
        span("12345678901-2", 50, 120), span("00001234567890", 220, 120),
    ])])
    items = DocumentIdentifierService().extract(normalized_document=document)
    assert {i["kind"] for i in items} == {"automatic_debit", "invoice"}
    for item in items:
        assert item["source"] == "NATIVE_SPAN"
        assert item["page_number"] == 2
        assert item["confidence"] is None
        assert item["coordinate_system"] == "pdf_points"
        assert item["value_region"]["top"] == 120


@pytest.mark.parametrize("digits", [
    "00190500954014481606906809350314337370000000100",
    "846800000065096900481001011294378606925069036430",
])
def test_existing_valid_payment_lines_are_not_retyped_by_length_or_grouping(digits):
    boxes = [_box(digits[i:i + 12], 100 + i * 12, 125) for i in range(0, len(digits), 12)]
    [line] = _read(boxes, " ".join(b.text for b in boxes))
    assert line.contextual_kind == "unclassified"
    assert NumericLineValidator().validate(line).status.value == "valid"


def test_repeated_values_on_different_pages_do_not_receive_arbitrary_field_provenance():
    values = ("123456789012", "00001234567890", "00009876543210")
    boxes = [_box(v, 100 + i * 160, 125, page=page)
             for page in (1, 2) for i, v in enumerate(values)]
    boxes += [_box("Nº da Conta", 260, 100), _box("Nº da Fatura", 420, 100)]
    lines = _read(boxes, "\n".join([" ".join(values)] * 2))
    assert len(lines) == 2
    assert all(line.contextual_kind == "unclassified" for line in lines)


def test_low_confidence_field_labels_do_not_suppress_numeric_candidate():
    values = ("123456789012", "00001234567890", "00009876543210")
    boxes = [_box(v, 100 + i * 160, 125) for i, v in enumerate(values)]
    labels = [_box("Nº da Conta", 260, 100), _box("Nº da Fatura", 420, 100)]
    for label in labels:
        label.confidence = 20
    [line] = _read(boxes + labels, " ".join(values))
    assert line.contextual_kind == "unclassified"


def test_native_numeric_observation_uses_native_geometry_not_ocr_boxes():
    values = ("123456789012", "00001234567890", "00009876543210")
    spans = []
    for i, (label, value) in enumerate(zip(
        ("Débito Automático", "Nº da Conta", "Nº da Fatura"), values,
    )):
        for text, y in ((label, 50), (value, 65)):
            spans.append(NS(text=text, page_number=1,
                            bounding_box=NS(left=50+i*100, top=y, right=130+i*100, bottom=y+8)))
    document = NS(pages=[NS(number=1, text_spans=spans)])
    fields = DocumentIdentifierService().extract(normalized_document=document)
    [line] = PrintedNumericLineReader().read(
        NS(content=" ".join(values)), NS(content=""),
        identifier_observations=fields, normalized_document=document,
    )
    assert line.source == "native_text"
    assert line.contextual_kind == "concatenated_fields"
    assert line.contextual_metadata["coordinate_system"] == "pdf_points"
