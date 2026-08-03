from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from app.domain.prompt_injection.models.prompt_injection_evidence import (
    PromptInjectionEvidence,
)


class BasePromptInjectionDetector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the stable detector name used in evidence metadata.
        """

    @abstractmethod
    def detect(
        self,
        *,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> Sequence[PromptInjectionEvidence]:
        """
        Analyze the supplied text and return zero or more evidences.

        The context may contain additional document information such as:

        - page number;
        - PDF text spans;
        - font size;
        - font color;
        - background color;
        - opacity;
        - bounding boxes;
        - OCR output;
        - rendered page information.

        Implementations must not mutate the supplied context.
        """