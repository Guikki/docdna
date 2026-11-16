from hashlib import sha256
from uuid import uuid4

from openpyxl import Workbook

from scripts import audit_exported_batch as audit


def test_audit_inspects_only_hash_verified_files_and_preserves_originals(tmp_path, monkeypatch):
    verified, changed, missing = [str(uuid4()) for _ in range(3)]
    original = b"synthetic test document"
    path = tmp_path / (verified + ".pdf")
    path.write_bytes(original)
    (tmp_path / (changed + ".pdf")).write_bytes(b"different version")
    book = Workbook()
    sheet = book.active
    sheet.title = "01 - Documentos"
    sheet.append(["ID da análise", "SHA-256"])
    for aid in (verified, changed, missing):
        sheet.append([aid, sha256(original).hexdigest()])
    workbook = tmp_path / "original.xlsx"
    book.save(workbook)
    workbook_bytes = workbook.read_bytes()
    calls = []

    def inspect(candidate):
        calls.append(candidate)
        return {"tiny_before": 65, "tiny_after": 0}

    monkeypatch.setattr(audit, "inspect_pdf", inspect)
    report = audit.audit_workbook(workbook, tmp_path)
    assert [r["status"] for r in report["documents"]] == [
        "INSPECTED_HASH_VERIFIED", "HASH_MISMATCH", "MISSING_PDF",
    ]
    assert calls == [path]
    assert path.read_bytes() == original
    assert workbook.read_bytes() == workbook_bytes


def test_inspection_failure_is_not_reported_as_absence_of_findings(tmp_path, monkeypatch):
    aid = str(uuid4())
    content = b"synthetic test document"
    (tmp_path / (aid + ".pdf")).write_bytes(content)
    book = Workbook()
    book.active.title = "01 - Documentos"
    book.active.append(["ID da análise", "SHA-256"])
    book.active.append([aid, sha256(content).hexdigest()])
    workbook = tmp_path / "original.xlsx"
    book.save(workbook)

    def fail(path):
        raise RuntimeError("unavailable OCR")

    monkeypatch.setattr(audit, "inspect_pdf", fail)
    [record] = audit.audit_workbook(workbook, tmp_path)["documents"]
    assert record["status"] == "INSPECTION_FAILED"
    assert record["error_type"] == "RuntimeError"
    assert "tiny_after" not in record
