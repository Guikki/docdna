"""Reprocessa localmente PDFs verificados contra um Excel, sem sobrescrevê-lo.

Executar da raiz com --workbook <xlsx> --output-dir <diretorio de auditoria>.
Produz novo lote/Excel e confere dashboards via TestClient, sem servidor externo.
"""
from argparse import ArgumentParser
from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from starlette.datastructures import Headers

from app.main import app
from app.domain.services.batch_processor import BatchProcessor
from app.domain.services.batch_excel_export_service import BatchExcelExportService
from app.infrastructure.repositories.analysis_memory_repository import AnalysisMemoryRepository


def workbook_metrics(path):
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = {s.title[:2]: list(s.values) for s in book}
        return {
            "sheet_rows": {s.title: s.max_row for s in book},
            "comparison_codes": dict(Counter(r[0] for r in rows["08"][1:])),
            "financial_values": sorted(
                (str(r[19]), str(r[20])) for r in rows["04"][1:]
                if r[19] in {"PRINTED", "ITF", "PIX"}
            ),
            "contextual_findings": sum(r[2] == "PAYMENT_LINE_INVALID_STRUCTURE"
                                       for r in rows["03"][1:]),
            "confidence_ratios": [r[12] for r in rows["07"][1:]],
            "numeric_observations": [
                {"filename": r[0], "line_index": r[3], "content": r[5],
                 "status": r[7], "message": r[13]}
                for r in rows["04"][1:] if str(r[2]).startswith("Valida")
            ],
        }
    finally:
        book.close()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reference", type=Path, action="append", default=[])
    args = parser.parse_args()
    protected = [args.workbook, *args.reference]
    hashes = {str(p): sha256(p.read_bytes()).hexdigest() for p in protected}
    book = load_workbook(args.workbook, read_only=True, data_only=True)
    try:
        rows = list(book["01 - Documentos"].values)[1:]
    finally:
        book.close()
    manifest = {"baseline_hashes": hashes, "baseline_metrics": workbook_metrics(args.workbook),
                "documents": []}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        uploads = []
        for row in rows:
            # Colunas históricas preservadas: documento, ID da análise, SHA-256.
            aid = str(UUID(row[8]))
            path = Path("storage/uploads") / (aid + ".pdf")
            digest = sha256(path.read_bytes()).hexdigest()
            if digest != row[10]:
                raise ValueError("PDF com hash diferente da exportação: " + aid)
            uploads.append(UploadFile(
                filename=row[0], file=stack.enter_context(path.open("rb")),
                headers=Headers({"content-type": "application/pdf"}),
            ))
            manifest["documents"].append({"filename": row[0], "sha256": digest,
                                           "source_analysis_id": aid})
        batch = BatchProcessor().process(uploads)
    if batch.result.completed_documents != len(rows) or batch.result.failed_documents:
        raise RuntimeError("Reprocessamento incompleto; conferir erros do lote")
    exported = BatchExcelExportService().export(batch)
    manifest.update(new_batch_id=str(batch.id), export=exported,
                    new_metrics=workbook_metrics(exported["file_path"]))
    if manifest["baseline_metrics"]["financial_values"] != manifest["new_metrics"]["financial_values"]:
        raise AssertionError("Os valores financeiros observados mudaram; investigar antes de concluir")
    original_numeric = {(r["filename"], r["line_index"], r["content"])
                        for r in manifest["baseline_metrics"]["numeric_observations"]}
    current_numeric = {(r["filename"], r["line_index"], r["content"])
                       for r in manifest["new_metrics"]["numeric_observations"]}
    if original_numeric != current_numeric:
        raise AssertionError("As observações numéricas originais não foram integralmente preservadas")
    manifest["raw_numeric_values_preserved"] = True
    client = TestClient(app)
    response = client.get("/batches/" + str(batch.id))
    response.raise_for_status()
    (args.output_dir / "dashboard.html").write_text(response.text, encoding="utf-8")
    manifest["dashboard_http_status"] = response.status_code
    repo = AnalysisMemoryRepository()
    for record, document in zip(manifest["documents"], batch.documents):
        analysis = repo.get_by_id(document.analysis_id)
        record.update(
            analysis_id=str(document.analysis_id),
            lines=[asdict(x) for x in analysis["printed_numeric_lines"]],
            numeric_locations=[asdict(x) for x in analysis["numeric_line_locations"]],
            identifiers=analysis["document_identifiers"],
            validation_statuses=[v.status.value for v in analysis["numeric_line_validations"]],
            comparison_statuses=[v.status.value for v in analysis["barcode_line_comparisons"]],
            contextual_findings=sum(e.code == "PAYMENT_LINE_INVALID_STRUCTURE"
                                    for e in analysis["evidences"]),
        )
        detail = client.get("/analyses/" + str(document.analysis_id) + "/investigations/financial")
        detail.raise_for_status()
        if any(x.contextual_kind == "concatenated_fields" for x in analysis["printed_numeric_lines"]):
            assert "Campos concatenados" in detail.text
        record["financial_dashboard_http_status"] = detail.status_code
        (args.output_dir / (str(document.analysis_id) + ".html")).write_text(detail.text, encoding="utf-8")
        print(record["filename"], [(x.digit_count, x.contextual_kind)
                                  for x in analysis["printed_numeric_lines"]], flush=True)
    if any(sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in hashes.items()):
        raise AssertionError("Uma exportação de referência foi alterada")
    (args.output_dir / "checkpoint.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print("EXPORT", exported["file_path"])
    print("COMPARISONS", manifest["new_metrics"]["comparison_codes"])


if __name__ == "__main__":
    main()
