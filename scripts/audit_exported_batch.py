"""Auditoria local reproduzível de PDFs vinculados a uma exportação Excel.

Executar na raiz: python -m scripts.audit_exported_batch --workbook <xlsx>
--output <json>. Não reprocessa uploads, não sobrescreve o Excel e não envia
documentos a serviços externos. O JSON contém métricas e hashes, sem payloads.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID

from openpyxl import load_workbook

from app.domain.concealment.services.qr_visual_concealment_correlator import QrVisualConcealmentCorrelator
from app.domain.concealment.services.visual_concealment_analysis_service import VisualConcealmentAnalysisService
from app.domain.document.adapters.native_document_adapter import NativeDocumentAdapter
from app.domain.readers.barcode_reader import BarcodeReader
from app.domain.readers.native_text_reader import NativeTextReader
from app.domain.readers.ocr_reader import OcrReader
from app.domain.readers.printed_numeric_line_reader import PrintedNumericLineReader
from app.domain.rules.numeric_line_validator import NumericLineValidator
from app.domain.services.document_identifier_service import DocumentIdentifierService
from app.domain.services.qr_structural_inspector import QrStructuralInspector


def inspect_pdf(path: Path) -> dict:
    native = NativeTextReader().read(str(path))
    ocr = OcrReader().read(str(path))
    reader = PrintedNumericLineReader()
    original = reader.read(native, ocr.document_ocr)
    recovered = reader.read(native, ocr.document_ocr, ocr_text_boxes=ocr.text_boxes)
    identifiers = DocumentIdentifierService().extract(
        native_text=native, ocr=ocr.document_ocr, ocr_text_boxes=ocr.text_boxes,
    )
    normalized = NativeDocumentAdapter().adapt(source=str(path))
    visual = VisualConcealmentAnalysisService().analyze(normalized, pdf_path=str(path))
    barcodes = BarcodeReader().read(str(path))
    structural = QrStructuralInspector().inspect_pdf(str(path), barcodes=barcodes)
    correlated = QrVisualConcealmentCorrelator().correlate(
        analysis=visual, normalized_document=normalized, qr_structural_findings=structural,
    )
    return {
        "native_character_count": native.character_count,
        "ocr_box_count": len(ocr.text_boxes),
        "aggregated_numeric_digit_counts": [x.digit_count for x in original],
        "geometric_numeric_digit_counts": [x.digit_count for x in recovered],
        "numeric_validation_statuses": dict(Counter(
            NumericLineValidator().validate(x).status.value for x in recovered
        )),
        "identifiers_by_kind": dict(Counter(x["kind"] for x in identifiers)),
        "missing_identifier_kinds": sorted(set(DocumentIdentifierService.LABELS)
                                          - {x["kind"] for x in identifiers}),
        "qr_structural_count": len(structural),
        "qr_matrix_statuses": dict(Counter(
            x["qr_matrix_validation"]["status"] for x in structural
        )),
        "tiny_before": visual.tiny_text_count,
        "tiny_after": correlated.tiny_text_count,
        "white_before": visual.white_text_count,
        "white_after": correlated.white_text_count,
        "low_contrast_before": visual.low_contrast_text_count,
        "low_contrast_after": correlated.low_contrast_text_count,
    }


def audit_workbook(workbook: Path, uploads: Path) -> dict:
    documents = []
    book = load_workbook(workbook, read_only=True, data_only=True)
    try:
        rows = iter(book["01 - Documentos"].values)
        headers = next(rows)
        for row in rows:
            values = dict(zip(headers, row))
            analysis_id = str(UUID(str(values["ID da análise"])))
            expected = str(values["SHA-256"] or "").lower()
            record = {"analysis_id": analysis_id, "expected_sha256": expected}
            documents.append(record)
            path = uploads / (analysis_id + ".pdf")
            if not path.is_file():
                record["status"] = "MISSING_PDF"
                continue
            actual = sha256(path.read_bytes()).hexdigest()
            record["actual_sha256"] = actual
            if actual != expected:
                record["status"] = "HASH_MISMATCH"
                continue
            try:
                record.update(inspect_pdf(path))
                record["status"] = "INSPECTED_HASH_VERIFIED"
            except Exception as error:
                # Uma falha não autoriza afirmar ausência de evidências.
                record["status"] = "INSPECTION_FAILED"
                record["error_type"] = type(error).__name__
    finally:
        book.close()
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "workbook_sha256": sha256(workbook.read_bytes()).hexdigest(),
        "scope": "Extração local e correlação QR/ocultação; não valida identidade com laudo externo.",
        "documents": documents,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--uploads", type=Path, default=Path("storage/uploads"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".json":
        parser.error("--output deve ser um arquivo .json separado da exportação original")
    result = audit_workbook(args.workbook, args.uploads)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(Counter(x["status"] for x in result["documents"])))
    return 0 if result["documents"] and all(
        x["status"] == "INSPECTED_HASH_VERIFIED" for x in result["documents"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
