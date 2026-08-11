from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.prompt_injection.services.prompt_phrase_catalog import (
    PromptPhraseCatalog,
    PromptPhraseRule,
)


def test_should_load_default_catalogs() -> None:
    catalog = PromptPhraseCatalog()

    assert catalog.rule_count > 0

    assert "pt-BR" in catalog.languages
    assert "en" in catalog.languages


def test_should_load_expected_categories() -> None:
    catalog = PromptPhraseCatalog()

    assert (
        "instruction_override"
        in catalog.categories
    )

    assert (
        "ai_targeting"
        in catalog.categories
    )

    assert (
        "role_manipulation"
        in catalog.categories
    )

    assert (
        "system_prompt_extraction"
        in catalog.categories
    )

    assert (
        "response_control"
        in catalog.categories
    )

    assert (
        "tool_manipulation"
        in catalog.categories
    )

    assert (
        "prompt_structure"
        in catalog.categories
    )


def test_should_return_rules_for_portuguese() -> None:
    catalog = PromptPhraseCatalog()

    rules = (
        catalog.rules_for_language(
            "pt-BR"
        )
    )

    assert rules

    assert all(
        rule.language == "pt-BR"
        for rule in rules
    )


def test_should_return_rules_for_english() -> None:
    catalog = PromptPhraseCatalog()

    rules = (
        catalog.rules_for_language(
            "en"
        )
    )

    assert rules

    assert all(
        rule.language == "en"
        for rule in rules
    )


def test_should_return_rules_for_category() -> None:
    catalog = PromptPhraseCatalog()

    rules = (
        catalog.rules_for_category(
            "instruction_override"
        )
    )

    assert rules

    assert all(
        rule.category
        == "instruction_override"
        for rule in rules
    )


def test_should_return_empty_tuple_for_unknown_language() -> None:
    catalog = PromptPhraseCatalog()

    result = (
        catalog.rules_for_language(
            "fr"
        )
    )

    assert result == ()


def test_should_return_empty_tuple_for_unknown_category() -> None:
    catalog = PromptPhraseCatalog()

    result = (
        catalog.rules_for_category(
            "unknown"
        )
    )

    assert result == ()


def test_grouped_by_language_should_be_immutable() -> None:
    catalog = PromptPhraseCatalog()

    grouped = (
        catalog.grouped_by_language()
    )

    with pytest.raises(
        TypeError
    ):
        grouped["pt-BR"] = ()  # type: ignore[index]


def test_rule_should_normalize_values() -> None:
    rule = PromptPhraseRule(
        language=" pt-BR ",
        category=" instruction_override ",
        phrase=(
            "  ignore   as instruções "
            "anteriores  "
        ),
    )

    assert rule.language == "pt-BR"

    assert (
        rule.category
        == "instruction_override"
    )

    assert (
        rule.phrase
        == "ignore as instruções anteriores"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("language", ""),
        ("language", "   "),
        ("category", ""),
        ("category", "   "),
        ("phrase", ""),
        ("phrase", "   "),
    ],
)
def test_rule_should_reject_empty_values(
    field: str,
    value: str,
) -> None:
    kwargs = {
        "language": "pt-BR",
        "category": (
            "instruction_override"
        ),
        "phrase": (
            "ignore instruções anteriores"
        ),
    }

    kwargs[field] = value

    with pytest.raises(
        ValueError
    ):
        PromptPhraseRule(
            **kwargs
        )


def test_should_reject_missing_catalog(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError
    ):
        PromptPhraseCatalog(
            rules_directory=tmp_path,
            catalog_files=(
                "missing.json",
            ),
        )


def test_should_reject_invalid_json(
    tmp_path: Path,
) -> None:
    file_path = (
        tmp_path
        / "invalid.json"
    )

    file_path.write_text(
        "{invalid",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid JSON",
    ):
        PromptPhraseCatalog(
            rules_directory=tmp_path,
            catalog_files=(
                "invalid.json",
            ),
        )


def test_should_reject_unsupported_schema(
    tmp_path: Path,
) -> None:
    file_path = (
        tmp_path
        / "catalog.json"
    )

    file_path.write_text(
        json.dumps(
            {
                "schema_version": 999,
                "language": "en",
                "categories": {
                    "test": [
                        "value"
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        PromptPhraseCatalog(
            rules_directory=tmp_path,
            catalog_files=(
                "catalog.json",
            ),
        )


def test_should_ignore_duplicated_rules(
    tmp_path: Path,
) -> None:
    file_path = (
        tmp_path
        / "catalog.json"
    )

    file_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "language": "en",
                "categories": {
                    "test": [
                        "ignore this",
                        "IGNORE THIS",
                        " ignore this ",
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    catalog = PromptPhraseCatalog(
        rules_directory=tmp_path,
        catalog_files=(
            "catalog.json",
        ),
    )

    assert catalog.rule_count == 1