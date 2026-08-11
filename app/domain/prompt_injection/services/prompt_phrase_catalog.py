from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class PromptPhraseRule:
    language: str
    category: str
    phrase: str

    def __post_init__(self) -> None:
        normalized_language = (
            self.language.strip()
        )

        normalized_category = (
            self.category.strip()
        )

        normalized_phrase = (
            " ".join(
                self.phrase.split()
            )
        )

        if not normalized_language:
            raise ValueError(
                "Prompt phrase language cannot be empty."
            )

        if not normalized_category:
            raise ValueError(
                "Prompt phrase category cannot be empty."
            )

        if not normalized_phrase:
            raise ValueError(
                "Prompt phrase cannot be empty."
            )

        object.__setattr__(
            self,
            "language",
            normalized_language,
        )

        object.__setattr__(
            self,
            "category",
            normalized_category,
        )

        object.__setattr__(
            self,
            "phrase",
            normalized_phrase,
        )


class PromptPhraseCatalog:
    """
    Carrega e consolida catálogos declarativos de frases
    relacionadas a possíveis tentativas de Prompt Injection.

    O catálogo não executa detecção e não calcula risco.
    """

    SUPPORTED_SCHEMA_VERSION = 1

    DEFAULT_RULES_DIRECTORY = (
        Path(__file__).resolve().parent.parent
        / "rules"
    )

    DEFAULT_CATALOG_FILES = (
        "prompt_phrases_pt_br.json",
        "prompt_phrases_en.json",
    )

    def __init__(
        self,
        *,
        rules_directory: Path | str | None = None,
        catalog_files: tuple[str, ...] | None = None,
    ) -> None:
        self._rules_directory = (
            Path(rules_directory)
            if rules_directory is not None
            else self.DEFAULT_RULES_DIRECTORY
        )

        self._catalog_files = (
            tuple(catalog_files)
            if catalog_files is not None
            else self.DEFAULT_CATALOG_FILES
        )

        self._rules = self._load_rules()

    @property
    def rules(
        self,
    ) -> tuple[PromptPhraseRule, ...]:
        return self._rules

    @property
    def rule_count(
        self,
    ) -> int:
        return len(self._rules)

    @property
    def languages(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                rule.language
                for rule in self._rules
            )
        )

    @property
    def categories(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                rule.category
                for rule in self._rules
            )
        )

    def rules_for_language(
        self,
        language: str,
    ) -> tuple[PromptPhraseRule, ...]:
        normalized_language = self._normalize_required_text(
            field_name="language",
            value=language,
        )

        return tuple(
            rule
            for rule in self._rules
            if rule.language.casefold()
            == normalized_language.casefold()
        )

    def rules_for_category(
        self,
        category: str,
    ) -> tuple[PromptPhraseRule, ...]:
        normalized_category = self._normalize_required_text(
            field_name="category",
            value=category,
        )

        return tuple(
            rule
            for rule in self._rules
            if rule.category.casefold()
            == normalized_category.casefold()
        )

    def grouped_by_language(
        self,
    ) -> Mapping[
        str,
        tuple[PromptPhraseRule, ...],
    ]:
        grouped = {
            language: self.rules_for_language(
                language
            )
            for language in self.languages
        }

        return MappingProxyType(
            grouped
        )

    def _load_rules(
        self,
    ) -> tuple[PromptPhraseRule, ...]:
        if not self._catalog_files:
            raise ValueError(
                "At least one prompt phrase catalog "
                "must be configured."
            )

        loaded_rules: list[
            PromptPhraseRule
        ] = []

        seen_rules: set[
            tuple[str, str, str]
        ] = set()

        for filename in self._catalog_files:
            catalog_path = (
                self._rules_directory
                / filename
            )

            catalog_data = (
                self._load_catalog_file(
                    catalog_path
                )
            )

            language = (
                self._extract_language(
                    catalog_data
                )
            )

            categories = (
                self._extract_categories(
                    catalog_data
                )
            )

            for category, phrases in (
                categories.items()
            ):
                normalized_category = (
                    self._normalize_required_text(
                        field_name="category",
                        value=category,
                    )
                )

                if not isinstance(
                    phrases,
                    list,
                ):
                    raise TypeError(
                        "Prompt phrase category "
                        f"'{normalized_category}' "
                        "must contain a list."
                    )

                for phrase in phrases:
                    if not isinstance(
                        phrase,
                        str,
                    ):
                        raise TypeError(
                            "Prompt phrase entries "
                            "must be strings."
                        )

                    rule = PromptPhraseRule(
                        language=language,
                        category=(
                            normalized_category
                        ),
                        phrase=phrase,
                    )

                    identity = (
                        rule.language.casefold(),
                        rule.category.casefold(),
                        rule.phrase.casefold(),
                    )

                    if identity in seen_rules:
                        continue

                    seen_rules.add(
                        identity
                    )

                    loaded_rules.append(
                        rule
                    )

        return tuple(
            loaded_rules
        )

    def _load_catalog_file(
        self,
        path: Path,
    ) -> dict:
        if not path.exists():
            raise FileNotFoundError(
                "Prompt phrase catalog not found: "
                f"{path}"
            )

        if not path.is_file():
            raise ValueError(
                "Prompt phrase catalog path must "
                f"reference a file: {path}"
            )

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(
                    file
                )

        except json.JSONDecodeError as error:
            raise ValueError(
                "Invalid JSON in prompt phrase "
                f"catalog: {path}"
            ) from error

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "Prompt phrase catalog root "
                "must be an object."
            )

        schema_version = data.get(
            "schema_version"
        )

        if schema_version != (
            self.SUPPORTED_SCHEMA_VERSION
        ):
            raise ValueError(
                "Unsupported prompt phrase "
                "catalog schema version: "
                f"{schema_version!r}."
            )

        return data

    def _extract_language(
        self,
        data: dict,
    ) -> str:
        language = data.get(
            "language"
        )

        return self._normalize_required_text(
            field_name="language",
            value=language,
        )

    @staticmethod
    def _extract_categories(
        data: dict,
    ) -> dict:
        categories = data.get(
            "categories"
        )

        if not isinstance(
            categories,
            dict,
        ):
            raise TypeError(
                "Prompt phrase catalog "
                "'categories' must be an object."
            )

        if not categories:
            raise ValueError(
                "Prompt phrase catalog must "
                "contain categories."
            )

        return categories

    @staticmethod
    def _normalize_required_text(
        *,
        field_name: str,
        value: object,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"Prompt phrase {field_name} "
                "must be a string."
            )

        normalized = (
            " ".join(
                value.split()
            )
        )

        if not normalized:
            raise ValueError(
                f"Prompt phrase {field_name} "
                "cannot be empty."
            )

        return normalized