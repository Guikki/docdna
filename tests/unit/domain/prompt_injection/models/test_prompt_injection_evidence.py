import pytest

from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)


def test_should_create_prompt_injection_evidence() -> None:
    evidence = PromptInjectionEvidence(
        code="prompt_injection_phrase",
        detector="PromptPhraseDetector",
        description="Suspicious instruction directed to an AI system.",
        confidence=0.95,
        weight=0.90,
        page_number=2,
        original_excerpt="Ignore previous instructions.",
        normalized_excerpt="ignore previous instructions",
        language="en",
        category="instruction_override",
        start_index=10,
        end_index=38,
        metadata={
            "matched_phrase": "ignore previous instructions",
        },
    )

    assert evidence.code == "PROMPT_INJECTION_PHRASE"
    assert evidence.detector == "PromptPhraseDetector"
    assert evidence.confidence == 0.95
    assert evidence.weight == 0.90
    assert evidence.page_number == 2
    assert evidence.language == "en"
    assert evidence.category == "instruction_override"
    assert evidence.weighted_score == pytest.approx(0.855)


def test_should_normalize_evidence_text_fields() -> None:
    evidence = PromptInjectionEvidence(
        code="  hidden_text_detected  ",
        detector="  HiddenTextDetector  ",
        description="  Hidden text was detected.  ",
        confidence=1.0,
        weight=0.8,
        language="  pt-BR  ",
        category="  hidden_text  ",
    )

    assert evidence.code == "HIDDEN_TEXT_DETECTED"
    assert evidence.detector == "HiddenTextDetector"
    assert evidence.description == "Hidden text was detected."
    assert evidence.language == "pt-BR"
    assert evidence.category == "hidden_text"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("code", ""),
        ("detector", ""),
        ("description", ""),
    ],
)
def test_should_reject_empty_required_text_fields(
    field_name: str,
    value: str,
) -> None:
    arguments = {
        "code": "TEST_CODE",
        "detector": "TestDetector",
        "description": "Test description.",
        "confidence": 0.5,
        "weight": 0.5,
    }

    arguments[field_name] = value

    with pytest.raises(ValueError):
        PromptInjectionEvidence(**arguments)


@pytest.mark.parametrize(
    "confidence",
    [-0.01, 1.01],
)
def test_should_reject_invalid_confidence(
    confidence: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="confidence must be between",
    ):
        PromptInjectionEvidence(
            code="TEST_CODE",
            detector="TestDetector",
            description="Test description.",
            confidence=confidence,
            weight=0.5,
        )


@pytest.mark.parametrize(
    "weight",
    [-0.01, 1.01],
)
def test_should_reject_invalid_weight(
    weight: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="weight must be between",
    ):
        PromptInjectionEvidence(
            code="TEST_CODE",
            detector="TestDetector",
            description="Test description.",
            confidence=0.5,
            weight=weight,
        )


def test_should_reject_page_number_lower_than_one() -> None:
    with pytest.raises(
        ValueError,
        match="page number",
    ):
        PromptInjectionEvidence(
            code="TEST_CODE",
            detector="TestDetector",
            description="Test description.",
            confidence=0.5,
            weight=0.5,
            page_number=0,
        )


def test_should_require_both_text_indexes() -> None:
    with pytest.raises(
        ValueError,
        match="must be provided together",
    ):
        PromptInjectionEvidence(
            code="TEST_CODE",
            detector="TestDetector",
            description="Test description.",
            confidence=0.5,
            weight=0.5,
            start_index=10,
        )


def test_should_reject_invalid_text_index_interval() -> None:
    with pytest.raises(
        ValueError,
        match="greater than start_index",
    ):
        PromptInjectionEvidence(
            code="TEST_CODE",
            detector="TestDetector",
            description="Test description.",
            confidence=0.5,
            weight=0.5,
            start_index=10,
            end_index=10,
        )


def test_should_copy_and_freeze_metadata() -> None:
    source_metadata = {
        "matched_phrase": "ignore previous instructions",
    }

    evidence = PromptInjectionEvidence(
        code="TEST_CODE",
        detector="TestDetector",
        description="Test description.",
        confidence=0.5,
        weight=0.5,
        metadata=source_metadata,
    )

    source_metadata["matched_phrase"] = "changed"

    assert (
        evidence.metadata["matched_phrase"]
        == "ignore previous instructions"
    )

    with pytest.raises(TypeError):
        evidence.metadata["new_key"] = "new_value"