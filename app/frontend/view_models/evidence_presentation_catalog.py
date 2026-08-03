from typing import Any


EVIDENCE_PRESENTATION_CATALOG: dict[str, dict[str, Any]] = {
    "DUPLICATE_ITF": {
        "category": "Código de barras",
        "display_title": "Código ITF repetido",
        "method_label": "Comparação de códigos ITF",
    },
    "DUPLICATE_ITF_DIFFERENT_NUMERIC_LINE": {
        "category": "Código de barras",
        "display_title": (
            "Código ITF repetido com "
            "sequências numéricas distintas"
        ),
        "method_label": (
            "Comparação entre ITF e sequência numérica"
        ),
    },
    "IMAGE_EXACT_MATCH": {
        "category": "Fingerprint de imagem",
        "display_title": "Imagem interna idêntica",
        "method_label": "Comparação criptográfica de imagens",
    },
    "IMAGE_STRONG_VISUAL_MATCH": {
        "category": "Fingerprint de imagem",
        "display_title": "Forte semelhança entre imagens",
        "method_label": "Comparação perceptual de imagens",
    },
    "IMAGE_VISUAL_MATCH": {
        "category": "Fingerprint de imagem",
        "display_title": "Semelhança visual entre imagens",
        "method_label": "Comparação perceptual de imagens",
    },
    "LOGO_EXACT_MATCH": {
        "category": "Fingerprint de logo",
        "display_title": "Logo idêntico localizado",
        "method_label": "Comparação criptográfica de logos",
    },
    "LOGO_STRONG_VISUAL_MATCH": {
        "category": "Fingerprint de logo",
        "display_title": "Forte semelhança visual entre logos",
        "method_label": "Comparação perceptual de logos",
    },
    "LOGO_VISUAL_MATCH": {
        "category": "Fingerprint de logo",
        "display_title": "Semelhança visual entre logos",
        "method_label": "Comparação perceptual de logos",
    },
    "LOGO_COMPANY_NAME_MISMATCH": {
        "category": "Fingerprint de logo",
        "display_title": (
            "Logo semelhante associado a empresas diferentes"
        ),
        "method_label": (
            "Correlação entre identidade visual e empresa"
        ),
    },
    "QRCODE_EXACT_MATCH": {
        "category": "Fingerprint de QR Code",
        "display_title": "QR Code idêntico localizado",
        "method_label": (
            "Comparação de conteúdo e imagem de QR Code"
        ),
    },
    "QRCODE_REGENERATED": {
        "category": "Fingerprint de QR Code",
        "display_title": "QR Code possivelmente regenerado",
        "method_label": (
            "Comparação entre conteúdo e representação visual"
        ),
    },
    "QRCODE_VALUE_MISMATCH": {
        "category": "Fingerprint de QR Code",
        "display_title": (
            "QR Code visualmente idêntico com conteúdo divergente"
        ),
        "method_label": (
            "Validação cruzada entre imagem e valor decodificado"
        ),
    },
}