from __future__ import annotations

from dataclasses import dataclass

from app.domain.concealment.models.text_concealment_finding import (
    TextConcealmentFinding,
)
from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)


@dataclass(frozen=True, slots=True)
class VisualConcealmentAnalysis:
    white_text_findings: tuple[TextConcealmentFinding, ...] = ()
    tiny_text_evidences: tuple[PromptInjectionEvidence, ...] = ()

    @property
    def total_findings(self) -> int:
        return len(self.white_text_findings) + len(self.tiny_text_evidences)

    @property
    def has_findings(self) -> bool:
        return self.total_findings > 0

    @property
    def white_text_count(self) -> int:
        return len(self.white_text_findings)

    @property
    def tiny_text_count(self) -> int:
        return len(self.tiny_text_evidences)

    @property
    def highest_confidence(self) -> float:
        confidences = [
            finding.confidence
            for finding in self.white_text_findings
        ]
        confidences.extend(
            evidence.confidence
            for evidence in self.tiny_text_evidences
        )
        if not confidences:
            return 0.0
        return max(confidences)