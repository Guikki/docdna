from __future__ import annotations

from dataclasses import dataclass

from app.domain.document.models.bounding_box import BoundingBox


@dataclass(frozen=True, slots=True)
class TextConcealmentFinding:
    """
    Achado objetivo de possível ocultação visual de texto.

    O modelo não declara fraude, Prompt Injection ou intenção maliciosa.
    Ele preserva fatos observados no documento e os sinais técnicos que
    justificaram o apontamento.
    """

    code: str
    detector: str
    page_number: int
    text: str
    bounding_box: BoundingBox
    font_name: str
    font_size: float
    font_color_hex: str
    confidence: float
    signals: tuple[str, ...]
    is_near_white: bool
    is_small_text: bool
    is_relative_small_text: bool
    is_instruction_like: bool

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def has_multiple_signals(self) -> bool:
        return self.signal_count >= 2