from __future__ import annotations

import sys
from pathlib import Path

from starlette.datastructures import (
    Headers,
    UploadFile,
)

from app.domain.use_cases.upload_document_use_case import (
    UploadDocumentUseCase,
)


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Uso:"
        )
        print(
            'python scripts/profile_document.py "C:\\caminho\\documento.pdf"'
        )
        raise SystemExit(1)

    pdf_path = Path(
        sys.argv[1]
    )

    if not pdf_path.exists():
        print(
            f"Arquivo não encontrado: {pdf_path}"
        )
        raise SystemExit(1)

    if (
        pdf_path.suffix.lower()
        != ".pdf"
    ):
        print(
            "O arquivo precisa ser PDF."
        )
        raise SystemExit(1)

    print()
    print(
        "=" * 72
    )
    print(
        "DocDNA — Perfil de desempenho"
    )
    print(
        "=" * 72
    )
    print(
        f"Arquivo: {pdf_path.name}"
    )
    print(
        f"Tamanho: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB"
    )
    print()

    with pdf_path.open(
        "rb"
    ) as file_handle:
        upload = UploadFile(
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

        result = (
            UploadDocumentUseCase()
            .execute(
                upload
            )
        )

    performance = result.get(
        "performance",
        {},
    )

    total_seconds = float(
        performance.get(
            "total_seconds",
            0.0,
        )
        or 0.0
    )

    stages = performance.get(
        "stages",
        {},
    )

    print(
        f"Tempo total: {total_seconds:.3f} s"
    )
    print()

    print(
        "ETAPAS"
    )
    print(
        "-" * 72
    )

    ordered_stages = sorted(
        stages.items(),
        key=lambda item: float(
            item[1].get(
                "duration_seconds",
                0.0,
            )
            or 0.0
        ),
        reverse=True,
    )

    for (
        stage_name,
        stage_data,
    ) in ordered_stages:
        duration = float(
            stage_data.get(
                "duration_seconds",
                0.0,
            )
            or 0.0
        )

        percentage = float(
            stage_data.get(
                "percentage_of_total",
                0.0,
            )
            or 0.0
        )

        calls = int(
            stage_data.get(
                "calls",
                0,
            )
            or 0
        )

        print(
            f"{stage_name:<38}"
            f"{duration:>10.3f} s"
            f"{percentage:>9.2f}%"
            f"{calls:>5}x"
        )

    measured_seconds = sum(
        float(
            stage.get(
                "duration_seconds",
                0.0,
            )
            or 0.0
        )
        for stage
        in stages.values()
    )

    unmeasured_seconds = max(
        total_seconds
        - measured_seconds,
        0.0,
    )

    print(
        "-" * 72
    )

    print(
        f"{'Tempo medido nas etapas':<38}"
        f"{measured_seconds:>10.3f} s"
    )

    print(
        f"{'Overhead / tempo não classificado':<38}"
        f"{unmeasured_seconds:>10.3f} s"
    )

    print(
        f"{'TOTAL':<38}"
        f"{total_seconds:>10.3f} s"
    )

    print()
    print(
        "=" * 72
    )


if __name__ == "__main__":
    main()