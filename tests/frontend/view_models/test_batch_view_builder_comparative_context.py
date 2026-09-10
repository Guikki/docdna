from datetime import datetime
from uuid import uuid4

from app.domain.models.batch import (
    Batch,
    BatchStatus,
)
from app.domain.models.batch_document import (
    BatchDocument,
    BatchDocumentStatus,
)
from app.domain.models.batch_result import (
    BatchResult,
)
from app.domain.models.cross_validation_finding import (
    CrossValidationFinding,
    CrossValidationSeverity,
)
from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)
from app.frontend.view_models.batch_view_builder import (
    BatchViewBuilder,
)


def _document(
    *,
    filename: str,
) -> BatchDocument:
    return BatchDocument(
        document_id=uuid4(),
        original_filename=filename,
        status=BatchDocumentStatus.COMPLETED,
        analysis_id=uuid4(),
        error_message=None,
    )


def _batch(
    documents: list[BatchDocument],
) -> Batch:
    now = datetime.now()

    return Batch(
        id=uuid4(),
        created_at=now,
        started_at=now,
        finished_at=now,
        status=BatchStatus.COMPLETED,
        documents=documents,
        result=BatchResult(
            total_documents=len(documents),
            pending_documents=0,
            processing_documents=0,
            completed_documents=len(documents),
            failed_documents=0,
            progress_percentage=100.0,
        ),
    )


def _finding(
    *,
    severity: CrossValidationSeverity,
    document_ids: list[str],
    code: str,
) -> CrossValidationFinding:
    return CrossValidationFinding(
        code=code,
        title=f"Finding {code}",
        description="Comparative test finding.",
        severity=severity,
        confidence=1.0,
        comparator="TestComparator",
        document_ids=document_ids,
        metadata={},
    )


def test_clear_document_should_keep_individual_status_and_receive_comparative_context():
    document = _document(
        filename="document.pdf"
    )
    batch = _batch(
        [document]
    )
    analysis_id = str(
        document.analysis_id
    )

    view = BatchViewBuilder().build(
        batch=batch,
        document_analytical_statuses={
            analysis_id: (
                InvestigationStatus.CLEAR
            )
        },
        comparative_findings=[
            _finding(
                severity=(
                    CrossValidationSeverity.INFO
                ),
                document_ids=[
                    analysis_id
                ],
                code="IMAGE_EXACT_MATCH",
            ),
            _finding(
                severity=(
                    CrossValidationSeverity.LOW
                ),
                document_ids=[
                    analysis_id
                ],
                code="QRCODE_REGENERATED",
            ),
        ],
    )

    exported_document = (
        view["documents"][0]
    )

    assert (
        exported_document[
            "analytical_status"
        ]
        == "clear"
    )

    assert (
        exported_document[
            "has_comparative_findings"
        ]
        is True
    )

    assert (
        exported_document[
            "comparative_finding_count"
        ]
        == 2
    )

    assert (
        exported_document[
            "comparative_finding_count_label"
        ]
        == "2 apontamentos comparativos"
    )

    assert (
        exported_document[
            "comparative_highest_severity"
        ]
        == "low"
    )

    assert (
        exported_document[
            "comparative_highest_severity_label"
        ]
        == "Baixo"
    )

    assert (
        exported_document[
            "comparative_url"
        ]
        == (
            f"/batches/{batch.id}/comparisons"
        )
    )


def test_document_without_comparative_findings_should_not_receive_comparative_badge():
    document = _document(
        filename="clean.pdf"
    )
    batch = _batch(
        [document]
    )

    view = BatchViewBuilder().build(
        batch=batch,
        document_analytical_statuses={
            str(document.analysis_id): (
                InvestigationStatus.CLEAR
            )
        },
        comparative_findings=[],
    )

    exported_document = (
        view["documents"][0]
    )

    assert (
        exported_document[
            "has_comparative_findings"
        ]
        is False
    )

    assert (
        exported_document[
            "comparative_finding_count"
        ]
        == 0
    )

    assert (
        exported_document[
            "comparative_highest_severity"
        ]
        is None
    )

    assert (
        exported_document[
            "comparative_url"
        ]
        is None
    )


def test_same_individual_priority_should_sort_by_comparative_severity():
    info_document = _document(
        filename="info.pdf"
    )
    high_document = _document(
        filename="high.pdf"
    )
    no_comparison_document = _document(
        filename="none.pdf"
    )

    documents = [
        no_comparison_document,
        info_document,
        high_document,
    ]

    batch = _batch(
        documents
    )

    statuses = {
        str(document.analysis_id): (
            InvestigationStatus.CLEAR
        )
        for document in documents
    }

    view = BatchViewBuilder().build(
        batch=batch,
        document_analytical_statuses=(
            statuses
        ),
        comparative_findings=[
            _finding(
                severity=(
                    CrossValidationSeverity.INFO
                ),
                document_ids=[
                    str(
                        info_document.analysis_id
                    )
                ],
                code="INFO_FINDING",
            ),
            _finding(
                severity=(
                    CrossValidationSeverity.HIGH
                ),
                document_ids=[
                    str(
                        high_document.analysis_id
                    )
                ],
                code="HIGH_FINDING",
            ),
        ],
    )

    filenames = [
        document[
            "original_filename"
        ]
        for document
        in view["documents"]
    ]

    assert filenames == [
        "high.pdf",
        "info.pdf",
        "none.pdf",
    ]
