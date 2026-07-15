from abc import ABC, abstractmethod

from app.domain.evidence.evidence import Evidence
from app.domain.models.analysis_context import AnalysisContext


class BaseDetector(ABC):

    @abstractmethod
    def analyze(self, context: AnalysisContext) -> list[Evidence]:
        pass