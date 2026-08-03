import pytest

from app.domain.prompt_injection.models.prompt_injection_assessment import (
    PromptInjectionAssessment,
)
from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)
from app.domain.prompt_injection.models.prompt_injection_risk_level import (
    PromptInjectionRiskLevel,
)


def build_evidence(
    *,
    code: str,
    detector: str,
    language: str | None = None,
) -> PromptInjectionEvidence:
    return PromptInjectionEvidence(
        code=code,
        detector=detector,
        description="Test evidence.",
        confidence=0.8,
        weight=0.7,
        language=language,
    )


def test_should_create_empty_assessment() -> None:
    assessment = PromptInjectionAssessment(
        score=0.0,
        risk_level=PromptInjectionRiskLevel.NONE,
    )

    assert assessment.score == 0.0
    assert assessment.risk_level is PromptInjectionRiskLevel.NONE
    assert assessment.evidences == ()
    assert assessment.has_evidences is False
    assert assessment.evidence_count == 0
    assert assessment.evidence_codes == ()
    assert assessment.detectors == ()
    assert assessment.languages_detected == ()


def test_should_create_assessment_with_evidences() -> None:
    first_evidence = build_evidence(
        code="PROMPT_INJECTION_PHRASE",
        detector="PromptPhraseDetector",
        language="pt-BR",
    )

    second_evidence = build_evidence(
        code="UNICODE_OBFUSCATION",
        detector="UnicodeObfuscationDetector",
        language="en",
    )

    assessment = PromptInjectionAssessment(
        score=0.85,
        risk_level=PromptInjectionRiskLevel.HIGH,
        evidences=(
            first_evidence,
            second_evidence,
        ),
        summary="  Suspicious prompt injection signals were detected.  ",
        metadata={
            "document_id": "document-001",
        },
    )

    assert assessment.has_evidences is True
    assert assessment.evidence_count == 2

    assert assessment.evidence_codes == (
        "PROMPT_INJECTION_PHRASE",
        "UNICODE_OBFUSCATION",
    )

    assert assessment.detectors == (
        "PromptPhraseDetector",
        "UnicodeObfuscationDetector",
    )

    assert assessment.languages_detected == (
        "pt-BR",
        "en",
    )

    assert (
        assessment.summary
        == "Suspicious prompt injection signals were detected."
    )


@pytest.mark.parametrize(
    "score",
    [-0.01, 1.01],
)
def test_should_reject_invalid_score(
    score: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="score must be",
    ):
        PromptInjectionAssessment(
            score=score,
            risk_level=PromptInjectionRiskLevel.LOW,
        )


def test_should_reject_invalid_risk_level() -> None:
    with pytest.raises(
        TypeError,
        match="PromptInjectionRiskLevel",
    ):
        PromptInjectionAssessment(
            score=0.5,
            risk_level="medium",
        )


def test_should_reject_invalid_evidence_type() -> None:
    with pytest.raises(
        TypeError,
        match="PromptInjectionEvidence",
    ):
        PromptInjectionAssessment(
            score=0.5,
            risk_level=PromptInjectionRiskLevel.MEDIUM,
            evidences=("invalid evidence",),
        )


def test_should_not_repeat_detector_names() -> None:
    first_evidence = build_evidence(
        code="FIRST_CODE",
        detector="PromptPhraseDetector",
        language="pt-BR",
    )

    second_evidence = build_evidence(
        code="SECOND_CODE",
        detector="PromptPhraseDetector",
        language="pt-BR",
    )

    assessment = PromptInjectionAssessment(
        score=0.7,
        risk_level=PromptInjectionRiskLevel.HIGH,
        evidences=(
            first_evidence,
            second_evidence,
        ),
    )

    assert assessment.detectors == (
        "PromptPhraseDetector",
    )

    assert assessment.languages_detected == (
        "pt-BR",
    )


def test_should_copy_and_freeze_metadata() -> None:
    source_metadata = {
        "document_id": "document-001",
    }

    assessment = PromptInjectionAssessment(
        score=0.0,
        risk_level=PromptInjectionRiskLevel.NONE,
        metadata=source_metadata,
    )

    source_metadata["document_id"] = "changed"

    assert assessment.metadata["document_id"] == "document-001"

    with pytest.raises(TypeError):
        assessment.metadata["new_key"] = "new_value"