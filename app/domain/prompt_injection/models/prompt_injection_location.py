from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class PromptInjectionLocation:
    """
    Representa a localização visual de uma evidência
    relacionada a possível Prompt Injection.

    Este modelo não determina se a evidência é verdadeira
    ou falsa.

    Sua responsabilidade é registrar onde o conteúdo
    associado à evidência foi localizado visualmente e,
    quando disponível, preservar metadados objetivos da
    origem textual utilizada na localização.

    A localização pode ter sido obtida a partir de:

    - texto nativo do PDF;
    - OCR;
    - outra fonte textual compatível no futuro.

    Campos tipográficos permanecem opcionais porque OCR
    não possui necessariamente informações reais de fonte.
    """

    evidence_index: int

    evidence_code: str
    detector: str

    page_number: int | None
    matched_content: str | None

    left: int | float | None
    top: int | float | None
    width: int | float | None
    height: int | float | None

    confidence: float | None

    source_image_path: str | None
    annotated_image_path: str | None

    located: bool
    message: str

    source: str | None = None

    font_name: str | None = None
    font_size: float | None = None
    font_color_hex: str | None = None

    is_tiny_text: bool | None = None
    is_white_text: bool | None = None