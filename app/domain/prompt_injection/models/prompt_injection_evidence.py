from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class PromptInjectionEvidence:
    code: str
    detector: str
    description: str
    confidence: float
    weight: float
    page_number: int | None = None
    original_excerpt: str | None = None
    normalized_excerpt: str | None = None
    language: str | None = None
    category: str | None = None
    start_index: int | None = None
    end_index: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_code = self.code.strip().upper()
        normalized_detector = self.detector.strip()
        normalized_description = self.description.strip()

        if not normalized_code:
            raise ValueError("Evidence code cannot be empty.")

        if not normalized_detector:
            raise ValueError("Evidence detector cannot be empty.")

        if not normalized_description:
            raise ValueError("Evidence description cannot be empty.")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Evidence confidence must be between 0.0 and 1.0."
            )

        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(
                "Evidence weight must be between 0.0 and 1.0."
            )

        if self.page_number is not None and self.page_number < 1:
            raise ValueError(
                "Evidence page number must be greater than or equal to 1."
            )

        if (self.start_index is None) != (self.end_index is None):
            raise ValueError(
                "Evidence start_index and end_index must be provided together."
            )

        if self.start_index is not None and self.end_index is not None:
            if self.start_index < 0:
                raise ValueError(
                    "Evidence start_index cannot be negative."
                )

            if self.end_index <= self.start_index:
                raise ValueError(
                    "Evidence end_index must be greater than start_index."
                )

        normalized_language = (
            self.language.strip()
            if self.language is not None and self.language.strip()
            else None
        )

        normalized_category = (
            self.category.strip()
            if self.category is not None and self.category.strip()
            else None
        )

        immutable_metadata = MappingProxyType(dict(self.metadata))

        object.__setattr__(self, "code", normalized_code)
        object.__setattr__(self, "detector", normalized_detector)
        object.__setattr__(self, "description", normalized_description)
        object.__setattr__(self, "language", normalized_language)
        object.__setattr__(self, "category", normalized_category)
        object.__setattr__(self, "metadata", immutable_metadata)

    @property
    def weighted_score(self) -> float:
        return self.confidence * self.weight