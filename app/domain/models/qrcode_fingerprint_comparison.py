from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QRCodeFingerprintComparison:
    """
    Representa o resultado técnico da comparação entre
    dois fingerprints de QR Code.

    O modelo registra apenas resultados objetivos da
    comparação. Ele não classifica fraude e não produz
    findings.

    O campo exact_image_match somente será verdadeiro
    quando ambos os hashes de imagem estiverem disponíveis
    e forem exatamente iguais.

    Os atributos opcionais possuem três estados:

    - True: ambos foram informados e são iguais;
    - False: ambos foram informados e são diferentes;
    - None: não havia dados suficientes para comparação.
    """

    exact_image_match: bool

    same_value: bool

    same_encoding: bool | None = None

    same_version: bool | None = None

    same_error_correction: bool | None = None

    rotation_difference: float = 0.0

    def __post_init__(self) -> None:
        if self.rotation_difference < 0:
            raise ValueError(
                "rotation_difference cannot be negative."
            )

    @property
    def has_encoding_comparison(self) -> bool:
        """
        Indica se os dois fingerprints possuíam
        informações de encoding comparáveis.
        """

        return self.same_encoding is not None

    @property
    def has_version_comparison(self) -> bool:
        """
        Indica se os dois fingerprints possuíam
        versões comparáveis.
        """

        return self.same_version is not None

    @property
    def has_error_correction_comparison(
        self,
    ) -> bool:
        """
        Indica se os dois fingerprints possuíam
        níveis de correção de erro comparáveis.
        """

        return (
            self.same_error_correction
            is not None
        )

    @property
    def has_same_rotation(self) -> bool:
        """
        Indica que os QR Codes foram detectados
        com a mesma rotação.
        """

        return self.rotation_difference == 0.0

    @property
    def is_same_qrcode(self) -> bool:
        """
        Considera que os QR Codes representam o mesmo
        conteúdo lógico quando os valores decodificados
        coincidem.

        A aparência visual não é exigida, pois um mesmo
        conteúdo pode ser regenerado, redimensionado ou
        processado novamente.
        """

        return self.same_value

    @property
    def is_visually_equal_but_value_changed(
        self,
    ) -> bool:
        """
        Indica o cenário crítico em que a imagem do QR Code
        é exatamente igual, mas o conteúdo decodificado
        diverge.
        """

        return (
            self.exact_image_match
            and not self.same_value
        )

    @property
    def is_same_value_with_different_image(
        self,
    ) -> bool:
        """
        Indica que o conteúdo é igual, embora os hashes
        das imagens não sejam idênticos.

        Isso pode ocorrer quando o QR Code é regenerado,
        redimensionado ou processado novamente.
        """

        return (
            self.same_value
            and not self.exact_image_match
        )