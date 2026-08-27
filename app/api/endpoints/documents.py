from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse

from app.domain.services.batch_excel_export_service import (
    BatchExcelExportService,
)
from app.domain.services.batch_processor import BatchProcessor
from app.domain.use_cases.upload_document_use_case import (
    UploadDocumentUseCase,
)
from app.infrastructure.repositories.analysis_memory_repository import (
    AnalysisMemoryRepository,
)
from app.infrastructure.repositories.batch_memory_repository import (
    BatchMemoryRepository,
)
from app.schemas.batch_export_schemas import (
    BatchExportResponse,
)
from app.schemas.batch_schemas import BatchResponse
from app.schemas.document_schemas import UploadDocumentResponse

from app.domain.services.batch_cross_validation_service import (
    BatchCrossValidationService,
)
from app.schemas.cross_validation_schemas import (
    CrossValidationFindingResponse,
    CrossValidationResultResponse,
)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

analysis_repository = AnalysisMemoryRepository()
batch_repository = BatchMemoryRepository()


@router.post(
    "/upload",
    response_model=UploadDocumentResponse,
    summary="Enviar um documento",
)
def upload_document(
    file: Annotated[
        UploadFile,
        File(
            description="Documento PDF que será analisado.",
        ),
    ],
) -> UploadDocumentResponse:
    try:
        use_case = UploadDocumentUseCase()
        result = use_case.execute(file)

        analysis_repository.save(
            analysis_id=result["id"],
            analysis_data=result,
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.post(
    "/batch-upload",
    response_model=BatchResponse,
    summary="Enviar um ou mais documentos",
)
def upload_document_batch(
    files: Annotated[
        list[UploadFile],
        File(
            description=(
                "Selecione um ou mais documentos PDF "
                "para processamento."
            ),
        ),
    ],
) -> BatchResponse:
    if not files:
        raise HTTPException(
            status_code=400,
            detail="Nenhum arquivo foi enviado.",
        )

    invalid_files = [
        file.filename or "arquivo sem nome"
        for file in files
        if (
            not file.filename
            or not file.filename.lower().endswith(".pdf")
        )
    ]

    if invalid_files:
        raise HTTPException(
            status_code=400,
            detail=(
                "O lote contém arquivos que não possuem "
                "a extensão PDF: "
                + ", ".join(invalid_files)
            ),
        )

    processor = BatchProcessor()
    batch = processor.process(files)

    return batch


@router.get(
    "/batches/{batch_id}",
    response_model=BatchResponse,
    summary="Consultar lote",
)
def get_document_batch(
    batch_id: UUID,
) -> BatchResponse:
    batch = batch_repository.get_by_id(batch_id)

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Lote não encontrado.",
        )

    return batch


@router.post(
    "/batches/{batch_id}/export",
    response_model=BatchExportResponse,
    summary="Gerar relatório Excel do lote",
)
def export_document_batch(
    batch_id: UUID,
) -> BatchExportResponse:
    batch = batch_repository.get_by_id(batch_id)

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Lote não encontrado.",
        )

    if batch.result.processing_documents > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "O lote ainda possui documentos em processamento. "
                "Aguarde a conclusão antes de gerar o relatório."
            ),
        )

    if batch.result.pending_documents > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "O lote ainda possui documentos pendentes. "
                "Aguarde a conclusão antes de gerar o relatório."
            ),
        )

    try:
        export_service = BatchExcelExportService()
        export_result = export_service.export(batch)

        # A URL pública é controlada por uma rota do FastAPI.
        export_result["download_url"] = (
            f"/documents/batches/{batch_id}/export/download"
        )

        return export_result

    except PermissionError as error:
        raise HTTPException(
            status_code=409,
            detail=(
                "O relatório não pôde ser sobrescrito. "
                "Verifique se o arquivo Excel está aberto "
                "e tente novamente."
            ),
        ) from error

    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Não foi possível salvar o relatório Excel "
                "no armazenamento local."
            ),
        ) from error


@router.get(
    "/batches/{batch_id}/export/download",
    summary="Baixar relatório Excel do lote",
    response_class=FileResponse,
)
def download_document_batch_export(
    batch_id: UUID,
) -> FileResponse:
    batch = batch_repository.get_by_id(batch_id)

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Lote não encontrado.",
        )

    try:
        export_service = BatchExcelExportService()

        # Geramos novamente para garantir que o arquivo
        # corresponda ao estado atual do lote.
        export_result = export_service.export(batch)

    except PermissionError as error:
        raise HTTPException(
            status_code=409,
            detail=(
                "O relatório não pôde ser atualizado. "
                "Feche o arquivo Excel que está aberto "
                "e tente novamente."
            ),
        ) from error

    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Não foi possível gerar o relatório Excel."
            ),
        ) from error

    file_path = Path(export_result["file_path"])

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="O arquivo de exportação não foi encontrado.",
        )

    return FileResponse(
        path=file_path,
        filename=export_result["filename"],
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


@router.get(
    "/batches/{batch_id}/cross-validation",
    response_model=CrossValidationResultResponse,
    summary="Executar validação cruzada do lote",
)
def get_batch_cross_validation(
    batch_id: UUID,
) -> CrossValidationResultResponse:
    batch = batch_repository.get_by_id(batch_id)

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Lote não encontrado.",
        )

    service = BatchCrossValidationService()
    result = service.execute(batch)

    findings = [
        CrossValidationFindingResponse(
            code=finding.code,
            title=finding.title,
            description=finding.description,
            severity=finding.severity.value,
            confidence=finding.confidence,
            comparator=finding.comparator,
            document_ids=finding.document_ids,
            metadata=finding.metadata,
        )
        for finding in result.findings
    ]

    return CrossValidationResultResponse(
        total_findings=result.total_findings,
        has_findings=result.has_findings,
        findings=findings,
    )
