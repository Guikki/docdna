from typing import Any
from uuid import UUID


class AnalysisMemoryRepository:
    _analyses: dict[UUID, dict[str, Any]] = {}

    def save(self, analysis_id: UUID, analysis_data: dict[str, Any]) -> None:
        self._analyses[analysis_id] = analysis_data

    def get_by_id(self, analysis_id: UUID) -> dict[str, Any] | None:
        return self._analyses.get(analysis_id)