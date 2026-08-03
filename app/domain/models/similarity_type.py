from __future__ import annotations

from enum import Enum


class SimilarityType(str, Enum):
    """
    Representa o tipo de similaridade identificada entre dois documentos.

    O valor de cada enum é utilizado tanto internamente quanto
    nas respostas da API e no frontend.
    """

    TEXT = "text"
    IMAGE = "image"
    BARCODE = "barcode"
    QRCODE = "qrcode"
    METADATA = "metadata"
    TEMPORAL = "temporal"
    VISUAL = "visual"
    FONT = "font"
    STRUCTURE = "structure"
    SIGNATURE = "signature"
    WATERMETER = "watermeter"
    LOGO = "logo"
    HASH = "hash"
    FILE = "file"

    @property
    def display_name(self) -> str:
        return {
            SimilarityType.TEXT: "Texto",
            SimilarityType.IMAGE: "Imagem",
            SimilarityType.BARCODE: "Código de barras",
            SimilarityType.QRCODE: "QR Code",
            SimilarityType.METADATA: "Metadados",
            SimilarityType.TEMPORAL: "Datas",
            SimilarityType.VISUAL: "Similaridade visual",
            SimilarityType.FONT: "Fontes",
            SimilarityType.STRUCTURE: "Estrutura",
            SimilarityType.SIGNATURE: "Assinatura",
            SimilarityType.WATERMETER: "Hidrômetro",
            SimilarityType.LOGO: "Logotipo",
            SimilarityType.HASH: "Hash",
            SimilarityType.FILE: "Arquivo",
        }[self]

    @property
    def icon(self) -> str:
        return {
            SimilarityType.TEXT: "description",
            SimilarityType.IMAGE: "image",
            SimilarityType.BARCODE: "barcode",
            SimilarityType.QRCODE: "qr_code",
            SimilarityType.METADATA: "dataset",
            SimilarityType.TEMPORAL: "schedule",
            SimilarityType.VISUAL: "visibility",
            SimilarityType.FONT: "text_fields",
            SimilarityType.STRUCTURE: "account_tree",
            SimilarityType.SIGNATURE: "draw",
            SimilarityType.WATERMETER: "water_drop",
            SimilarityType.LOGO: "copyright",
            SimilarityType.HASH: "fingerprint",
            SimilarityType.FILE: "insert_drive_file",
        }[self]

    @property
    def frontend_color(self) -> str:
        return {
            SimilarityType.TEXT: "blue",
            SimilarityType.IMAGE: "purple",
            SimilarityType.BARCODE: "orange",
            SimilarityType.QRCODE: "orange",
            SimilarityType.METADATA: "cyan",
            SimilarityType.TEMPORAL: "green",
            SimilarityType.VISUAL: "pink",
            SimilarityType.FONT: "indigo",
            SimilarityType.STRUCTURE: "teal",
            SimilarityType.SIGNATURE: "red",
            SimilarityType.WATERMETER: "blue",
            SimilarityType.LOGO: "amber",
            SimilarityType.HASH: "gray",
            SimilarityType.FILE: "slate",
        }[self]