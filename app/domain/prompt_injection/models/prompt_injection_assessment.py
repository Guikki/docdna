from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)
from app.domain.prompt_injection.models.prompt_injection_risk_level import (
    PromptInjectionRiskLevel,
)


@dataclass(frozen=True, slots=True)
class PromptInjectionAssessment:
    score: float
    risk_level: PromptInjectionRiskLevel
    evidences: tuple[PromptInjectionEvidence, ...] = ()
    summary: str | None = None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                "Prompt injection assessment score must be "
                "between 0.0 and 1.0."
            )

        if not isinstance(self.risk_level, PromptInjectionRiskLevel):
            raise TypeError(
                "Prompt injection assessment risk_level must be a "
                "PromptInjectionRiskLevel."
            )

        normalized_evidences = tuple(self.evidences)

        for evidence in normalized_evidences:
            if not isinstance(evidence, PromptInjectionEvidence):
                raise TypeError(
                    "All assessment evidences must be "
                    "PromptInjectionEvidence instances."
                )

        normalized_summary = (
            self.summary.strip()
            if self.summary is not None and self.summary.strip()
            else None
        )

        immutable_metadata = MappingProxyType(dict(self.metadata or {}))

        object.__setattr__(self, "evidences", normalized_evidences)
        object.__setattr__(self, "summary", normalized_summary)
        object.__setattr__(self, "metadata", immutable_metadata)

    @property
    def has_evidences(self) -> bool:
        return bool(self.evidences)

    @property
    def evidence_count(self) -> int:
        return len(self.evidences)

    @property
    def evidence_codes(self) -> tuple[str, ...]:
        return tuple(evidence.code for evidence in self.evidences)

    @property
    def detectors(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                evidence.detector
                for evidence in self.evidences
            )
        )

    @property
    def languages_detected(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                evidence.language
                for evidence in self.evidences
                if evidence.language is not None
            )
        )