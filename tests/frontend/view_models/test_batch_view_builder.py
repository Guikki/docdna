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
from app.frontend.investigations.models.investigation_status import (
    InvestigationStatus,
)
from app.frontend.view_models.batch_view_builder import (
    BatchViewBuilder,
)


def _document(
    *,
    filename: str,
):
    return BatchDocument(
        document_id=uuid4(),
        original_filename=filename,
        status=(
            BatchDocumentStatus.COMPLETED
        ),
        analysis_id=uuid4(),
        error_message=None,
    )


def _batch(
    documents,
):
    return Batch(
        id=uuid4(),
        created_at=datetime.now(),
        started_at=datetime.now(),
        finished_at=datetime.now(),
        status=BatchStatus.COMPLETED,
        documents=list(documents),
        result=BatchResult(
            total_documents=len(
                documents
            ),
            pending_documents=0,
            processing_documents=0,
            completed_documents=len(
                documents
            ),
            failed_documents=0,
            progress_percentage=100.0,
        ),
    )


def test_should_assign_analytical_status_to_each_document():
    alert_document = _document(
        filename="alert.pdf"
    )

    clear_document = _document(
        filename="clear.pdf"
    )

    batch = _batch(
        [
            clear_document,
            alert_document,
        ]
    )

    statuses = {
        str(
            alert_document.analysis_id
        ): InvestigationStatus.ALERT,

        str(
            clear_document.analysis_id
        ): InvestigationStatus.CLEAR,
    }

    view = BatchViewBuilder().build(
        batch=batch,
        document_analytical_statuses=(
            statuses
        ),
    )

    assert (
        view["documents"][0][
            "original_filename"
        ]
        == "alert.pdf"
    )

    assert (
        view["documents"][0][
            "analytical_status"
        ]
        == "alert"
    )

    assert (
        view["documents"][0][
            "analytical_status_label"
        ]
        == "Alta prioridade"
    )


def test_alert_document_should_make_batch_alert():
    alert_document = _document(
        filename="alert.pdf"
    )

    attention_document = _document(
        filename="attention.pdf"
    )

    clear_document = _document(
        filename="clear.pdf"
    )

    batch = _batch(
        [
            clear_document,
            attention_document,
            alert_document,
        ]
    )

    statuses = {
        str(
            alert_document.analysis_id
        ): InvestigationStatus.ALERT,

        str(
            attention_document.analysis_id
        ): InvestigationStatus.ATTENTION,

        str(
            clear_document.analysis_id
        ): InvestigationStatus.CLEAR,
    }

    view = BatchViewBuilder().build(
        batch=batch,
        document_analytical_statuses=(
            statuses
        ),
    )

    assert (
        view["analytical_status"]
        == "alert"
    )

    assert (
        view[
            "analytical_status_label"
        ]
        == "Alta prioridade"
    )


def test_should_count_document_statuses():
    documents = [
        _document(
            filename="a.pdf"
        ),
        _document(
            filename="b.pdf"
        ),
        _document(
            filename="c.pdf"
        ),
        _document(
            filename="d.pdf"
        ),
    ]

    batch = _batch(
        documents
    )

    statuses = {
        str(
            documents[0].analysis_id
        ): InvestigationStatus.ALERT,

        str(
            documents[1].analysis_id
        ): InvestigationStatus.ATTENTION,

        str(
            documents[2].analysis_id
        ): InvestigationStatus.ATTENTION,

        str(
            documents[3].analysis_id
        ): InvestigationStatus.CLEAR,
    }

    view = BatchViewBuilder().build(
        batch=batch,
        document_analytical_statuses=(
            statuses
        ),
    )

    summary = (
        view[
            "analytical_summary"
        ]
    )

    assert (
        summary[
            "alert_documents"
        ]
        == 1
    )

    assert (
        summary[
            "attention_documents"
        ]
        == 2
    )

    assert (
        summary[
            "clear_documents"
        ]
        == 1
    )

    assert (
        summary[
            "not_executed_documents"
        ]
        == 0
    )


def test_documents_should_be_sorted_by_analytical_priority():
    documents = [
        _document(
            filename="clear.pdf"
        ),
        _document(
            filename="attention.pdf"
        ),
        _document(
            filename="alert.pdf"
        ),
    ]

    batch = _batch(
        documents
    )

    statuses = {
        str(
            documents[0].analysis_id
        ): InvestigationStatus.CLEAR,

        str(
            documents[1].analysis_id
        ): InvestigationStatus.ATTENTION,

        str(
            documents[2].analysis_id
        ): InvestigationStatus.ALERT,
    }

    view = BatchViewBuilder().build(
        batch=batch,
        document_analytical_statuses=(
            statuses
        ),
    )

    filenames = [
        document[
            "original_filename"
        ]
        for document
        in view["documents"]
    ]

    assert filenames == [
        "alert.pdf",
        "attention.pdf",
        "clear.pdf",
    ]


def test_missing_analytical_status_should_be_not_executed():
    document = _document(
        filename="unknown.pdf"
    )

    batch = _batch(
        [document]
    )

    view = BatchViewBuilder().build(
        batch=batch,
    )

    assert (
        view["documents"][0][
            "analytical_status"
        ]
        == "not_executed"
    )

    assert (
        view["analytical_summary"][
            "not_executed_documents"
        ]
        == 1
    )

    assert (
        view["analytical_status"]
        == "not_executed"
    )