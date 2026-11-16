from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.domain.models.ocr_text_box import OcrTextBox
from app.domain.readers.printed_numeric_line_reader import PrintedNumericLineReader
from app.domain.rules.numeric_line_validator import NumericLineValidator


def _boxes():
    return [OcrTextBox(
        page_number=1, text=text, confidence=92,
        left=100 + i * 130, top=500, width=100, height=12,
    ) for i, text in enumerate((
        "012345678901", "234567890123", "456789012345", "678901234567",
    ))]


def _read(boxes, ocr=""):
    return PrintedNumericLineReader().read(
        native_text=SimpleNamespace(content=""),
        ocr=SimpleNamespace(content=ocr), ocr_text_boxes=boxes,
    )


def test_recovers_visual_line_from_shuffled_ocr_blocks_without_changing_digits():
    boxes = _boxes()
    result = _read(boxes[::-1], "\n".join(b.text for b in boxes[::-1]))
    assert len(result) == 1
    assert result[0].normalized_content == "".join(b.text for b in boxes)
    assert result[0].source == "ocr"
    assert result[0].digit_count == 48
    assert result[0].raw_content.startswith("012345678901 ")
    assert NumericLineValidator().validate(result[0]).status.value == "inconclusive"


@pytest.mark.parametrize("change", [
    {"page_number": 2}, {"top": 530}, {"left": 1000},
    {"text": "6789O1234567"}, {"text": "67890123456"},
    {"width": 0}, {"top": float("nan")},
])
def test_does_not_join_different_pages_rows_distant_columns_or_uncertain_digits(change):
    boxes = _boxes()
    boxes[-1] = replace(boxes[-1], **change)
    assert _read(boxes) == []


def test_existing_ocr_occurrence_is_not_duplicated_by_geometric_fallback():
    boxes = _boxes()
    assert len(_read(boxes, " ".join(b.text for b in boxes))) == 1


def test_five_adjacent_identifiers_are_not_sliced_into_payment_line():
    boxes = _boxes()
    boxes.append(replace(boxes[-1], left=620))
    assert _read(boxes) == []


def test_intervening_word_prevents_joining_numeric_columns():
    boxes = _boxes()
    boxes.append(replace(boxes[0], text="Total", left=205, width=20))
    assert _read(boxes) == []
