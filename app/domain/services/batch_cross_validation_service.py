from typing import Any

from app.domain.builders.evidence_report_builder import (
    EvidenceReportBuilder,
)
from app.domain.comparators.cross_validation_engine import (
    CrossValidationEngine,
)
from app.domain.comparators.duplicate_itf_comparator import (
    DuplicateItfComparator,
)
from app.domain.comparators.duplicate_itf_different_numeric_line_comparator import (
    DuplicateItfDifferentNumericLineComparator,
)
from app.domain.models.batch import Batch
from app.domain.models.cross_validation_result import (
    CrossValidationResult,
)
from app.domain.models.evidence_report import EvidenceReport
from app.infrastructure.repositories.analysis_memory_repository import (
    AnalysisMemoryRepository,
)


class BatchCrossValidationService:

    def __init__(self) -> None:
        self._analysis_repository = AnalysisMemoryRepository()

        self._engine = CrossValidationEngine(
            comparators=[
                DuplicateItfComparator(),
                DuplicateItfDifferentNumericLineComparator(),
            ]
        )

        self._evidence_report_builder = (
            EvidenceReportBuilder()
        )

    def execute(
        self,
        batch: Batch,
    ) -> CrossValidationResult:
        """
        Executa a validação cruzada do lote.

        Este método preserva o contrato atualmente utilizado
        pela rota da API, retornando somente o resultado técnico
        da validação cruzada.
        """
        analyses = self._load_batch_analyses(batch)

        if len(analyses) < 2:
            return CrossValidationResult(
                findings=[]
            )

        return self._engine.execute(
            analyses=analyses
        )

    def build_evidence_report(
        self,
        batch: Batch,
    ) -> EvidenceReport:
        """
        Executa a validação cruzada e transforma os achados
        técnicos em evidências padronizadas.
        """
        cross_validation_result = self.execute(batch)

        return self._evidence_report_builder.build(
            cross_validation_result
        )

    def execute_with_report(
        self,
        batch: Batch,
    ) -> tuple[
        CrossValidationResult,
        EvidenceReport,
    ]:
        """
        Retorna, em uma única operação, o resultado técnico
        e o relatório amigável de evidências.

        Este método será utilizado pela interface do lote
        e pela exportação em Excel.
        """
        cross_validation_result = self.execute(batch)

        evidence_report = (
            self._evidence_report_builder.build(
                cross_validation_result
            )
        )

        return (
            cross_validation_result,
            evidence_report,
        )

    def _load_batch_analyses(
        self,
        batch: Batch,
    ) -> list[dict[str, Any]]:
        analyses: list[dict[str, Any]] = []

        for batch_document in batch.documents:
            analysis_id = batch_document.analysis_id

            if analysis_id is None:
                continue

            analysis = (
                self._analysis_repository.get_by_id(
                    analysis_id
                )
            )

            if analysis is None:
                continue

            analyses.append(analysis)

        return analyses