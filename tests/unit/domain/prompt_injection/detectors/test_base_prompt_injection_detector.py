from typing import Any

import pytest

from app.domain.prompt_injection.detectors.base_prompt_injection_detector import (
    BasePromptInjectionDetector,
)
from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)


class FakePromptInjectionDetector(BasePromptInjectionDetector):
    @property
    def name(self) -> str:
        return "FakePromptInjectionDetector"

    def detect(
        self,
        *,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[PromptInjectionEvidence, ...]:
        if "suspicious" not in text.lower():
            return ()

        return (
            PromptInjectionEvidence(
                code="FAKE_EVIDENCE",
                detector=self.name,
                description="Fake suspicious content was detected.",
                confidence=1.0,
                weight=0.5,
                metadata={
                    "context_received": context is not None,
                },
            ),
        )


def test_should_not_instantiate_abstract_detector() -> None:
    with pytest.raises(TypeError):
        BasePromptInjectionDetector()


def test_should_execute_concrete_detector() -> None:
    detector = FakePromptInjectionDetector()

    evidences = detector.detect(
        text="This is suspicious content.",
        context={
            "page_number": 1,
        },
    )

    assert detector.name == "FakePromptInjectionDetector"
    assert len(evidences) == 1
    assert evidences[0].code == "FAKE_EVIDENCE"
    assert evidences[0].detector == detector.name


def test_should_return_empty_sequence_when_no_evidence_exists() -> None:
    detector = FakePromptInjectionDetector()

    evidences = detector.detect(
        text="Ordinary document content.",
    )

    assert evidences == ()