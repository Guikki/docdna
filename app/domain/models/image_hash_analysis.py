from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImageHashAnalysis:
    """
    Representa os hashes calculados para uma imagem extraída
    de um documento.

    O objeto contém:

    - perceptual_hash: hash perceptual baseado em frequência;
    - average_hash: hash baseado na média de luminosidade;
    - difference_hash: hash baseado nas diferenças entre pixels;
    - image_hash: hash criptográfico SHA-256 do arquivo original.

    Este model apenas representa o resultado técnico da análise.
    Ele não realiza comparação nem produz conclusões.
    """

    perceptual_hash: str
    average_hash: str
    difference_hash: str
    image_hash: str

    def __post_init__(self) -> None:
        self._validate_hash(
            field_name="perceptual_hash",
            value=self.perceptual_hash,
        )
        self._validate_hash(
            field_name="average_hash",
            value=self.average_hash,
        )
        self._validate_hash(
            field_name="difference_hash",
            value=self.difference_hash,
        )
        self._validate_hash(
            field_name="image_hash",
            value=self.image_hash,
        )

    @staticmethod
    def _validate_hash(
        field_name: str,
        value: str,
    ) -> None:
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string."
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} cannot be empty."
            )