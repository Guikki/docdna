from __future__ import annotations


def canonicalize_trimmed(
    value: str,
) -> str:
    """
    Remove apenas espaços externos.

    É o canonicalizer mais conservador.
    Útil quando o conteúdo interno é semanticamente
    significativo e não deve ser alterado.
    """
    value = _require_string(value)

    result = value.strip()

    if not result:
        raise ValueError(
            "Canonical value must not be empty."
        )

    return result


def canonicalize_casefolded_text(
    value: str,
) -> str:
    """
    Remove espaços externos e normaliza diferenças
    de maiúsculas/minúsculas.

    Não remove pontuação, acentos ou espaços internos.
    """
    return canonicalize_trimmed(
        value
    ).casefold()


def canonicalize_digits(
    value: str,
) -> str:
    """
    Mantém apenas caracteres numéricos.

    Adequado para domínios nos quais pontuação e
    formatação visual não integram o valor lógico,
    como CPF/CNPJ e determinados números estruturados.
    """
    value = _require_string(value)

    result = "".join(
        character
        for character in value
        if character.isdigit()
    )

    if not result:
        raise ValueError(
            "Canonical value must contain at least one digit."
        )

    return result


def canonicalize_compact_alphanumeric(
    value: str,
) -> str:
    """
    Mantém somente caracteres alfanuméricos e aplica
    casefold.

    Deve ser usado apenas em domínios nos quais
    pontuação e espaços não possuam significado.
    """
    value = _require_string(value)

    result = "".join(
        character.casefold()
        for character in value
        if character.isalnum()
    )

    if not result:
        raise ValueError(
            "Canonical value must contain at least "
            "one alphanumeric character."
        )

    return result


def _require_string(
    value: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            "Value to canonicalize must be a string."
        )

    return value