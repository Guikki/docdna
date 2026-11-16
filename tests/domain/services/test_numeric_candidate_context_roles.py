from types import SimpleNamespace as NS

from app.domain.models.printed_numeric_line import PrintedNumericLine
from app.domain.rules.numeric_line_validator import NumericLineValidator
from app.domain.detectors.barcode_numeric_line_detector import BarcodeNumericLineDetector
from app.domain.comparators.duplicate_itf_different_numeric_line_comparator import DuplicateItfDifferentNumericLineComparator
from app.domain.services.batch_excel_export_service import BatchExcelExportService


def _context(digits, confidence=95):
    line = PrintedNumericLine(1, "ocr", digits, digits, len(digits))
    return NS(printed_numeric_lines=[line], numeric_line_validations=[NumericLineValidator().validate(line)],
              numeric_line_locations=[NS(line_index=1, located=True, page_number=1,
                                        matched_content=digits, confidence=confidence,
                                        left=100, top=300, width=400, height=12)],
              saved_path="not-a-pdf", ocr_text_boxes=[], barcodes=[])


def test_valid_format_and_trusted_location_is_candidate_without_claiming_linkage():
    context = _context("00190500954014481606906809350314337370000000100")
    [line] = BarcodeNumericLineDetector().classify_candidates(context)
    assert line.contextual_kind == "payment_line_candidate"
    assert line.contextual_metadata["association_status"] == "CONTEXTUAL_NOT_PROVEN"
    assert context.numeric_line_validations[0].status.value == "valid"


def test_unknown_48_digits_and_short_itf_do_not_establish_payment_context():
    context = _context("4" * 48)
    context.barcodes = [NS(format="ITF", content="00104360", page_number=1)]
    [line] = BarcodeNumericLineDetector().classify_candidates(context)
    assert line.contextual_kind == "unresolved_numeric_sequence"
    assert context.numeric_line_validations[0].status.value == "inconclusive"


def test_low_confidence_preserves_observed_page_and_geometry_without_trusting_it():
    context = _context("4" * 48, confidence=29)
    [line] = BarcodeNumericLineDetector().classify_candidates(context)
    assert line.contextual_kind == "unresolved_numeric_sequence"
    assert line.contextual_metadata["page_number"] == 1
    assert line.contextual_metadata["confidence_ocr_percent"] == 29
    assert line.contextual_metadata["bounds_ocr_pixels"] == (100, 300, 500, 312)


def test_comparator_preserves_three_roles_and_excludes_only_proven_concatenation():
    payment = PrintedNumericLine(1, "ocr", "8" * 48, "8" * 48, 48,
                                contextual_kind="payment_line_candidate")
    fields = PrintedNumericLine(2, "ocr", "2" * 40, "2" * 40, 40,
                               contextual_kind="concatenated_fields")
    unresolved = PrintedNumericLine(1, "ocr", "4" * 48, "4" * 48, 48,
                                   contextual_kind="unresolved_numeric_sequence")
    analyses = [{"id": aid, "barcodes": [NS(format="ITF", content="00104360")],
                 "printed_numeric_lines": lines}
                for aid, lines in (("a", [payment, fields]), ("b", [unresolved]))]
    [finding] = DuplicateItfDifferentNumericLineComparator().compare(analyses)
    documents = finding.metadata["documents"]
    assert documents[0]["numeric_lines"] == [payment.normalized_content]
    assert documents[1]["numeric_lines"] == [unresolved.normalized_content]
    assert {x["role"] for d in documents for x in d["numeric_line_contexts"]} == {
        "payment_line_candidate", "observed_concatenated_identifiers", "unresolved_numeric_sequence",
    }
    text = BatchExcelExportService()._format_comparison_numeric_lines(finding.metadata)
    assert "sequência inconclusiva" in text
    assert "candidata de pagamento; vínculo não confirmado" in text
    assert fields.normalized_content not in text
