from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import api_router
from app.config.settings import settings
from app.domain.services.batch_cross_validation_service import (
    BatchCrossValidationService,
)
from app.frontend.investigations.builders.investigation_view_builder import (
    InvestigationViewBuilder,
)
from app.frontend.view_models.analysis_view_builder import (
    AnalysisViewBuilder,
)
from app.frontend.view_models.batch_view_builder import (
    BatchViewBuilder,
)
from app.frontend.view_models.comparison_view_builder import (
    ComparisonViewBuilder,
)
from app.frontend.view_models.evidence_report_view_builder import (
    EvidenceReportViewBuilder,
)
from app.infrastructure.repositories.analysis_memory_repository import (
    AnalysisMemoryRepository,
)
from app.infrastructure.repositories.batch_memory_repository import (
    BatchMemoryRepository,
)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_SLOGAN,
    version="0.1.0",
)


# Arquivos estáticos do frontend
app.mount(
    "/static",
    StaticFiles(
        directory=settings.STATIC_DIR
    ),
    name="static",
)


# Evidências e imagens extraídas
settings.EXTRACTED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

app.mount(
    "/extracted",
    StaticFiles(
        directory=settings.EXTRACTED_DIR
    ),
    name="extracted",
)


# Templates HTML
templates = Jinja2Templates(
    directory=str(
        settings.TEMPLATES_DIR
    )
)


# Repositório e builders da análise individual
analysis_repository = (
    AnalysisMemoryRepository()
)

analysis_view_builder = (
    AnalysisViewBuilder()
)

investigation_view_builder = (
    InvestigationViewBuilder()
)


# Repositório e builders da análise em lote
batch_repository = (
    BatchMemoryRepository()
)

batch_view_builder = (
    BatchViewBuilder()
)

batch_cross_validation_service = (
    BatchCrossValidationService()
)

evidence_report_view_builder = (
    EvidenceReportViewBuilder()
)

comparison_view_builder = (
    ComparisonViewBuilder()
)


# Rotas da API
app.include_router(
    api_router
)


def _fix_binary_file_schemas(
    value: Any,
) -> None:
    """
    Corrige a representação de arquivos binários
    no schema OpenAPI.

    Algumas versões do FastAPI geram:

        contentMediaType:
            application/octet-stream

    O Swagger UI espera:

        format: binary

    A função percorre recursivamente todo o schema,
    inclusive arrays.
    """

    if isinstance(
        value,
        dict,
    ):
        content_media_type = (
            value.get(
                "contentMediaType"
            )
        )

        if (
            value.get("type") == "string"
            and content_media_type
            in {
                "application/octet-stream",
                "application/pdf",
            }
        ):
            value.pop(
                "contentMediaType",
                None,
            )

            value["format"] = "binary"

        for nested_value in (
            value.values()
        ):
            _fix_binary_file_schemas(
                nested_value
            )

    elif isinstance(
        value,
        list,
    ):
        for nested_value in value:
            _fix_binary_file_schemas(
                nested_value
            )


def custom_openapi() -> dict[str, Any]:
    """
    Gera e armazena o schema OpenAPI corrigido.
    """

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    _fix_binary_file_schemas(
        openapi_schema
    )

    app.openapi_schema = (
        openapi_schema
    )

    return app.openapi_schema


# Substitui apenas a geração do schema
# utilizado pelo Swagger.
app.openapi = custom_openapi


@app.get("/")
def home(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="pages/home.html",
        context={
            "project_name": (
                settings.PROJECT_NAME
            ),
            "project_slogan": (
                settings.PROJECT_SLOGAN
            ),
        },
    )


@app.get("/upload")
def upload_page(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="pages/upload.html",
        context={
            "project_name": (
                settings.PROJECT_NAME
            ),
            "project_slogan": (
                settings.PROJECT_SLOGAN
            ),
        },
    )


@app.get("/analyses/{analysis_id}")
def analysis_result(
    request: Request,
    analysis_id: UUID,
):
    """
    Exibe o panorama executivo da análise.

    A página principal não apresenta diretamente
    todos os dados técnicos.

    Os resultados são organizados em investigações
    temáticas pelo InvestigationViewBuilder.
    """

    analysis_data = (
        analysis_repository.get_by_id(
            analysis_id
        )
    )

    if analysis_data is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Análise não encontrada."
            ),
        )

    analysis_view = (
        analysis_view_builder.build(
            analysis_data
        )
    )

    analysis_view[
        "investigations"
    ] = (
        investigation_view_builder.build_cards(
            analysis_id=analysis_id,
            analysis_view=analysis_view,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name=(
            "pages/"
            "analysis_result.html"
        ),
        context={
            "project_name": (
                settings.PROJECT_NAME
            ),
            "project_slogan": (
                settings.PROJECT_SLOGAN
            ),
            "analysis": analysis_view,
        },
    )


@app.get(
    "/analyses/{analysis_id}"
    "/investigations/"
    "{investigation_slug}"
)
def investigation_detail(
    request: Request,
    analysis_id: UUID,
    investigation_slug: str,
):
    """
    Exibe o relatório detalhado de uma
    investigação específica.

    Exemplos:

    /investigations/identity
    /investigations/structure
    /investigations/content
    /investigations/visual
    /investigations/financial
    /investigations/evidence
    """

    analysis_data = (
        analysis_repository.get_by_id(
            analysis_id
        )
    )

    if analysis_data is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Análise não encontrada."
            ),
        )

    analysis_view = (
        analysis_view_builder.build(
            analysis_data
        )
    )

    try:
        detail_view = (
            investigation_view_builder.build_detail(
                analysis_id=analysis_id,
                slug=investigation_slug,
                analysis_view=analysis_view,
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return templates.TemplateResponse(
        request=request,
        name=(
            "pages/"
            "investigation_detail.html"
        ),
        context={
            "project_name": (
                settings.PROJECT_NAME
            ),
            "project_slogan": (
                settings.PROJECT_SLOGAN
            ),
            **detail_view,
        },
    )


@app.get("/batches/{batch_id}")
def batch_result(
    request: Request,
    batch_id: UUID,
):
    batch = (
        batch_repository.get_by_id(
            batch_id
        )
    )

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Lote não encontrado."
            ),
        )

    batch_view = (
        batch_view_builder.build(
            batch
        )
    )

    evidence_report = (
        batch_cross_validation_service
        .build_evidence_report(
            batch
        )
    )

    evidence_report_view = (
        evidence_report_view_builder
        .build(
            evidence_report
        )
    )

    return templates.TemplateResponse(
        request=request,
        name=(
            "pages/"
            "batch_result.html"
        ),
        context={
            "project_name": (
                settings.PROJECT_NAME
            ),
            "project_slogan": (
                settings.PROJECT_SLOGAN
            ),
            "batch": batch_view,
            "evidence_report": (
                evidence_report_view
            ),
        },
    )


@app.get(
    "/batches/{batch_id}/comparisons"
)
def batch_comparisons(
    request: Request,
    batch_id: UUID,
):
    batch = (
        batch_repository.get_by_id(
            batch_id
        )
    )

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Lote não encontrado."
            ),
        )

    batch_view = (
        batch_view_builder.build(
            batch
        )
    )

    evidence_report = (
        batch_cross_validation_service
        .build_evidence_report(
            batch
        )
    )

    comparison_view = (
        comparison_view_builder.build(
            report=evidence_report,
            batch_view=batch_view,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name=(
            "pages/"
            "batch_comparison.html"
        ),
        context={
            "project_name": (
                settings.PROJECT_NAME
            ),
            "project_slogan": (
                settings.PROJECT_SLOGAN
            ),
            "comparison": (
                comparison_view
            ),
        },
    )