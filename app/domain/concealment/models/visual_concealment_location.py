from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VisualConcealmentLocation:
    """
    Representa a localização visual de um achado de ocultação textual.

    As coordenadas left/top/width/height permanecem na escala nativa
    do PDF. As imagens produzidas pelo builder são artefatos derivados
    para revisão humana.

    O modelo não conclui fraude, Prompt Injection ou intenção maliciosa.
    """

    finding_index: int
    finding_code: str
    detector: str
    page_number: int
    matched_content: str
    left: float
    top: float
    width: float
    height: float
    confidence: float
    source_image_path: str
    annotated_image_path: str
    located: bool
    message: str
    font_name: str | None = None
    font_size: float | None = None
    font_color_hex: str | None = None

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height