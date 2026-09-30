from __future__ import annotations

import sys
from pathlib import Path

from starlette.datastructures import (
    Headers,
    UploadFile,
)

from app.domain.services.batch_cross_validation_service import (
    BatchCrossValidationService,
)
from app.domain.services.batch_processor import (
    BatchProcessor,
)


def _collect_pdf_paths(
    arguments: list[str],
) -> list[Path]:
    paths: list[Path] = []

    for argument in arguments:
        path = Path(argument)

        if path.is_dir():
            paths.extend(
                sorted(
                    item
                    for item in path.glob("*.pdf")
                    if item.is_file()
                )
            )
            continue

        if (
            path.is_file()
            and path.suffix.lower() == ".pdf"
        ):
            paths.append(path)
            continue

        raise ValueError(
            f"Caminho inválido ou não-PDF: {path}"
        )

    unique_paths: list[Path] = []
    seen: set[str] = set()

    for path in paths:
        key = str(
            path.resolve()
        ).lower()

        if key in seen:
            continue

        seen.add(key)
        unique_paths.append(path)

    return unique_paths


def _print_batch_report(
    report: dict,
) -> None:
    print()
    print("=" * 88)
    print("DocDNA — Perfil de desempenho do lote")
    print("=" * 88)

    print(
        f"Documentos: {report.get('documents_total', 0)}"
    )
    print(
        f"Concluídos: {report.get('completed_documents', 0)}"
    )
    print(
        f"Falhas: {report.get('failed_documents', 0)}"
    )
    print(
        f"Tempo total do lote: "
        f"{float(report.get('total_seconds', 0.0)):.3f} s"
    )
    print(
        f"Tempo acumulado das análises: "
        f"{float(report.get('document_analysis_seconds', 0.0)):.3f} s"
    )
    print(
        f"Média por documento: "
        f"{float(report.get('average_document_wall_seconds', 0.0)):.3f} s"
    )

    fastest = report.get(
        "fastest_document"
    )

    slowest = report.get(
        "slowest_document"
    )

    if fastest:
        print(
            "Mais rápido: "
            f"{fastest.get('filename')} "
            f"({float(fastest.get('wall_seconds', 0.0)):.3f} s)"
        )

    if slowest:
        print(
            "Mais lento: "
            f"{slowest.get('filename')} "
            f"({float(slowest.get('wall_seconds', 0.0)):.3f} s)"
        )

    print()
    print("ETAPAS AGREGADAS DOS DOCUMENTOS")
    print("-" * 88)

    stages = report.get(
        "stages",
        {},
    )

    for (
        name,
        data,
    ) in sorted(
        stages.items(),
        key=lambda item: float(
            item[1].get(
                "duration_seconds",
                0.0,
            )
            or 0.0
        ),
        reverse=True,
    ):
        print(
            f"{name:<42}"
            f"{float(data.get('duration_seconds', 0.0)):>10.3f} s"
            f"{float(data.get('percentage_of_document_analysis', 0.0)):>9.2f}%"
            f"{int(data.get('calls', 0)):>6}x"
        )

    print()
    print("ORQUESTRAÇÃO DO LOTE")
    print("-" * 88)

    orchestration = report.get(
        "orchestration",
        {},
    )

    for (
        name,
        data,
    ) in sorted(
        orchestration.items(),
        key=lambda item: float(
            item[1].get(
                "duration_seconds",
                0.0,
            )
            or 0.0
        ),
        reverse=True,
    ):
        print(
            f"{name:<42}"
            f"{float(data.get('duration_seconds', 0.0)):>10.6f} s"
            f"{int(data.get('calls', 0)):>6}x"
        )


def _print_cross_validation_report(
    report: dict,
) -> None:
    print()
    print("VALIDAÇÃO CRUZADA")
    print("=" * 88)

    print(
        f"Análises carregadas: "
        f"{report.get('analyses_loaded', 0)}"
    )

    metrics = report.get(
        "engine_metrics",
        {},
    )

    print(
        "Comparadores executados: "
        f"{metrics.get('comparators_executed', 0)}"
    )
    print(
        "Achados gerados: "
        f"{metrics.get('findings_generated', 0)}"
    )
    print(
        "Tempo interno da engine: "
        f"{float(metrics.get('execution_time_ms', 0.0)):.3f} ms"
    )
    print(
        "Tempo total validação + relatório: "
        f"{float(report.get('total_seconds', 0.0)):.3f} s"
    )
    image_selection = report.get(
        "image_candidate_selection"
    )

    if image_selection:
        print()
        print(
            "SELEÇÃO DE CANDIDATOS VISUAIS"
        )
        print("-" * 88)

        print(
            "Documentos considerados: "
            f"{image_selection.get('documents_total', 0)}"
        )

        print(
            "Fingerprints analisados: "
            f"{image_selection.get('fingerprints_total', 0):,}"
        )

        print(
            "Pares potenciais: "
            f"{image_selection.get('potential_cross_document_pairs', 0):,}"
        )

        print(
            "Pares candidatos: "
            f"{image_selection.get('candidate_pairs', 0):,}"
        )

        print(
            "Pares com SHA-256 exato: "
            f"{image_selection.get('exact_sha256_pairs', 0):,}"
        )

        print(
            "Pares somente perceptuais: "
            f"{image_selection.get('perceptual_only_pairs', 0):,}"
        )

        print(
            "Redução do espaço de busca: "
            f"{float(image_selection.get('reduction_percentage', 0.0)):.4f}%"
        )

    print()
    print("ETAPAS")
    print("-" * 88)

    for (
        name,
        data,
    ) in report.get(
        "stages",
        {},
    ).items():
        print(
            f"{name:<42}"
            f"{float(data.get('duration_seconds', 0.0)):>10.6f} s"
            f"{int(data.get('calls', 0)):>6}x"
        )


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso:")
        print(
            'python -m scripts.profile_batch '
            '"C:\\pasta\\com\\pdfs"'
        )
        print("ou:")
        print(
            'python -m scripts.profile_batch '
            '"C:\\a.pdf" "C:\\b.pdf"'
        )
        raise SystemExit(1)

    try:
        pdf_paths = _collect_pdf_paths(
            sys.argv[1:]
        )
    except ValueError as error:
        print(str(error))
        raise SystemExit(1) from error

    if not pdf_paths:
        print("Nenhum PDF encontrado.")
        raise SystemExit(1)

    print(
        f"Preparando {len(pdf_paths)} documento(s)..."
    )

    opened_files = []
    uploads = []

    try:
        for pdf_path in pdf_paths:
            file_handle = pdf_path.open(
                "rb"
            )

            opened_files.append(
                file_handle
            )

            uploads.append(
                UploadFile(
                    file=file_handle,
                    filename=pdf_path.name,
                    headers=Headers(
                        {
                            "content-type": (
                                "application/pdf"
                            )
                        }
                    ),
                )
            )

        processor = BatchProcessor()

        batch = processor.process(
            uploads
        )

        batch_report = (
            processor.performance_report
            or {}
        )

        _print_batch_report(
            batch_report
        )

        cross_validation_service = (
            BatchCrossValidationService()
        )

        cross_validation_service.execute_with_report(
            batch
        )

        cross_report = (
            cross_validation_service
            .performance_report
            or {}
        )

        _print_cross_validation_report(
            cross_report
        )

    finally:
        for file_handle in opened_files:
            file_handle.close()


if __name__ == "__main__":
    main()