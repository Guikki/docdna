from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Any

from app.domain.prompt_injection.detectors.base_prompt_injection_detector import (
    BasePromptInjectionDetector,
)
from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)
from app.domain.prompt_injection.services.prompt_phrase_catalog import (
    PromptPhraseCatalog,
    PromptPhraseRule,
)


class PromptPhraseDetector(
    BasePromptInjectionDetector
):
    """
    Detecta frases e estruturas textuais associadas a possíveis
    tentativas de Prompt Injection.

    O detector trabalha sobre catálogos declarativos de regras em
    português-BR e inglês.

    A presença de uma frase não confirma Prompt Injection.

    Este componente apenas produz evidências técnicas que deverão ser
    posteriormente consolidadas por um assessment.
    """

    DETECTOR_NAME = "prompt_phrase_detector"

    CATEGORY_WEIGHTS = {
        "instruction_override": 0.95,
        "ai_targeting": 0.60,
        "role_manipulation": 0.80,
        "system_prompt_extraction": 1.00,
        "response_control": 0.55,
        "tool_manipulation": 0.85,
        "prompt_structure": 0.50,
    }

    CATEGORY_CONFIDENCE = {
        "instruction_override": 0.95,
        "ai_targeting": 0.75,
        "role_manipulation": 0.85,
        "system_prompt_extraction": 0.98,
        "response_control": 0.70,
        "tool_manipulation": 0.90,
        "prompt_structure": 0.65,
    }

    CATEGORY_DESCRIPTIONS = {
        "instruction_override": (
            "Foi identificada uma instrução textual que pode "
            "tentar substituir, ignorar ou sobrescrever "
            "instruções anteriores."
        ),
        "ai_targeting": (
            "Foi identificado texto aparentemente direcionado "
            "explicitamente a um sistema de inteligência artificial."
        ),
        "role_manipulation": (
            "Foi identificada linguagem que pode tentar alterar "
            "o papel ou comportamento de um sistema de IA."
        ),
        "system_prompt_extraction": (
            "Foi identificada linguagem associada à tentativa "
            "de obter instruções internas ou prompt de sistema."
        ),
        "response_control": (
            "Foi identificada linguagem que pode tentar controlar "
            "diretamente o formato ou conteúdo da resposta de um "
            "sistema de IA."
        ),
        "tool_manipulation": (
            "Foi identificada linguagem que pode tentar instruir "
            "um sistema de IA a utilizar ferramentas, comandos "
            "ou recursos externos."
        ),
        "prompt_structure": (
            "Foi identificada uma estrutura textual semelhante "
            "a marcadores usados em prompts ou mensagens internas "
            "de sistemas de IA."
        ),
    }

    def __init__(
        self,
        *,
        catalog: PromptPhraseCatalog | None = None,
    ) -> None:
        self._catalog = (
            catalog
            if catalog is not None
            else PromptPhraseCatalog()
        )

    @property
    def name(self) -> str:
        return self.DETECTOR_NAME

    def detect(
        self,
        *,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> Sequence[PromptInjectionEvidence]:
        if not isinstance(text, str):
            raise TypeError(
                "PromptPhraseDetector text must be a string."
            )

        if context is not None and not isinstance(
            context,
            dict,
        ):
            raise TypeError(
                "PromptPhraseDetector context must be "
                "a dictionary or None."
            )

        if not text.strip():
            return ()

        normalized_text = self._normalize_text(
            text
        )

        if not normalized_text:
            return ()

        page_number = self._extract_page_number(
            context
        )

        evidences: list[
            PromptInjectionEvidence
        ] = []

        seen_matches: set[
            tuple[
                str,
                str,
                int,
                int,
            ]
        ] = set()

        for rule in self._catalog.rules:
            matches = self._find_rule_matches(
                original_text=text,
                normalized_text=normalized_text,
                rule=rule,
            )

            for match in matches:
                identity = (
                    rule.language.casefold(),
                    rule.category.casefold(),
                    match["start_index"],
                    match["end_index"],
                )

                if identity in seen_matches:
                    continue

                seen_matches.add(
                    identity
                )

                evidences.append(
                    self._build_evidence(
                        rule=rule,
                        original_text=text,
                        matched_text=match[
                            "matched_text"
                        ],
                        normalized_match=match[
                            "normalized_match"
                        ],
                        start_index=match[
                            "start_index"
                        ],
                        end_index=match[
                            "end_index"
                        ],
                        page_number=page_number,
                        context=context,
                    )
                )

        return tuple(
            sorted(
                evidences,
                key=lambda evidence: (
                    evidence.start_index
                    if evidence.start_index
                    is not None
                    else -1,
                    -evidence.weight,
                ),
            )
        )

    def _find_rule_matches(
        self,
        *,
        original_text: str,
        normalized_text: str,
        rule: PromptPhraseRule,
    ) -> list[dict[str, Any]]:
        normalized_phrase = (
            self._normalize_text(
                rule.phrase
            )
        )

        if not normalized_phrase:
            return []

        pattern = self._build_phrase_pattern(
            normalized_phrase
        )

        results: list[
            dict[str, Any]
        ] = []

        for match in re.finditer(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        ):
            normalized_start = (
                match.start()
            )

            normalized_end = (
                match.end()
            )

            original_range = (
                self._map_normalized_range_to_original(
                    original_text=original_text,
                    normalized_start=normalized_start,
                    normalized_end=normalized_end,
                )
            )

            if original_range is None:
                continue

            original_start, original_end = (
                original_range
            )

            matched_text = original_text[
                original_start:original_end
            ]

            results.append(
                {
                    "matched_text": (
                        matched_text
                    ),
                    "normalized_match": (
                        match.group(0)
                    ),
                    "start_index": (
                        original_start
                    ),
                    "end_index": (
                        original_end
                    ),
                }
            )

        return results

    @staticmethod
    def _build_phrase_pattern(
        normalized_phrase: str,
    ) -> str:
        escaped_parts = [
            re.escape(part)
            for part in normalized_phrase.split()
        ]

        core_pattern = r"\s+".join(
            escaped_parts
        )

        first_character = (
            normalized_phrase[0]
        )

        last_character = (
            normalized_phrase[-1]
        )

        prefix = (
            r"(?<!\w)"
            if first_character.isalnum()
            else ""
        )

        suffix = (
            r"(?!\w)"
            if last_character.isalnum()
            else ""
        )

        return (
            prefix
            + core_pattern
            + suffix
        )

    def _build_evidence(
        self,
        *,
        rule: PromptPhraseRule,
        original_text: str,
        matched_text: str,
        normalized_match: str,
        start_index: int,
        end_index: int,
        page_number: int | None,
        context: dict[str, Any] | None,
    ) -> PromptInjectionEvidence:
        category = rule.category

        confidence = (
            self.CATEGORY_CONFIDENCE.get(
                category,
                0.60,
            )
        )

        weight = (
            self.CATEGORY_WEIGHTS.get(
                category,
                0.50,
            )
        )

        description = (
            self.CATEGORY_DESCRIPTIONS.get(
                category,
                (
                    "Foi identificado um padrão textual "
                    "associado a possíveis instruções "
                    "direcionadas a sistemas de IA."
                ),
            )
        )

        excerpt = self._build_excerpt(
            text=original_text,
            start_index=start_index,
            end_index=end_index,
        )

        metadata = {
            "matched_rule": rule.phrase,
            "catalog_language": (
                rule.language
            ),
            "category_weight": weight,
            "detector_version": 1,
        }

        if context:
            source = context.get(
                "source"
            )

            if isinstance(
                source,
                str,
            ) and source.strip():
                metadata[
                    "source"
                ] = source.strip()

        return PromptInjectionEvidence(
            code=self._build_code(
                category
            ),
            detector=self.name,
            description=description,
            confidence=confidence,
            weight=weight,
            page_number=page_number,
            original_excerpt=excerpt,
            normalized_excerpt=(
                normalized_match
            ),
            language=rule.language,
            category=category,
            start_index=start_index,
            end_index=end_index,
            metadata=metadata,
        )

    @staticmethod
    def _build_code(
        category: str,
    ) -> str:
        normalized_category = (
            re.sub(
                r"[^A-Z0-9]+",
                "_",
                category.upper(),
            )
            .strip("_")
        )

        return (
            "PROMPT_INJECTION_"
            f"{normalized_category}"
        )

    @staticmethod
    def _build_excerpt(
        *,
        text: str,
        start_index: int,
        end_index: int,
        context_size: int = 80,
    ) -> str:
        excerpt_start = max(
            0,
            start_index - context_size,
        )

        excerpt_end = min(
            len(text),
            end_index + context_size,
        )

        excerpt = text[
            excerpt_start:excerpt_end
        ]

        return " ".join(
            excerpt.split()
        )

    @staticmethod
    def _extract_page_number(
        context: dict[str, Any] | None,
    ) -> int | None:
        if not context:
            return None

        value = context.get(
            "page_number"
        )

        if value is None:
            return None

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise TypeError(
                "PromptPhraseDetector context "
                "page_number must be an integer."
            )

        if value < 1:
            raise ValueError(
                "PromptPhraseDetector context "
                "page_number must be greater "
                "than or equal to 1."
            )

        return value

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        decomposed = (
            unicodedata.normalize(
                "NFKD",
                value,
            )
        )

        without_accents = "".join(
            character
            for character in decomposed
            if not unicodedata.combining(
                character
            )
        )

        normalized_spaces = (
            " ".join(
                without_accents.split()
            )
        )

        return (
            normalized_spaces.casefold()
        )

    def _map_normalized_range_to_original(
        self,
        *,
        original_text: str,
        normalized_start: int,
        normalized_end: int,
    ) -> tuple[int, int] | None:
        """
        Reconstrói aproximadamente o intervalo correspondente
        no texto original.

        Como normalização remove acentos e comprime espaços,
        não podemos assumir que os índices normalizados são
        idênticos aos índices originais.
        """

        normalized_position = 0

        original_start: int | None = None
        original_end: int | None = None

        previous_was_space = False

        for index, character in enumerate(
            original_text
        ):
            normalized_character = (
                self._normalize_character(
                    character
                )
            )

            if not normalized_character:
                continue

            is_space = (
                normalized_character
                == " "
            )

            if (
                is_space
                and previous_was_space
            ):
                continue

            previous_was_space = is_space

            character_length = len(
                normalized_character
            )

            next_position = (
                normalized_position
                + character_length
            )

            if (
                original_start is None
                and next_position
                > normalized_start
            ):
                original_start = index

            if (
                original_start is not None
                and normalized_position
                < normalized_end
                <= next_position
            ):
                original_end = (
                    index + 1
                )
                break

            normalized_position = (
                next_position
            )

        if original_start is None:
            return None

        if original_end is None:
            original_end = len(
                original_text
            )

        return (
            original_start,
            original_end,
        )

    @staticmethod
    def _normalize_character(
        value: str,
    ) -> str:
        if value.isspace():
            return " "

        decomposed = (
            unicodedata.normalize(
                "NFKD",
                value,
            )
        )

        normalized = "".join(
            character
            for character in decomposed
            if not unicodedata.combining(
                character
            )
        )

        return normalized.casefold()