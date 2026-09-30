from __future__ import annotations

from uuid import UUID, uuid5


class ForensicElementIdentityFactory:
    """
    Gera identificadores determinísticos para elementos forenses.

    O mesmo documento, com a mesma chave de origem, produzirá sempre
    o mesmo UUID. Isso permite reprocessamento, retry, importação e
    persistência sem criar duplicatas silenciosas.

    A identidade representa a ocorrência técnica do dado, e não
    necessariamente o seu conteúdo.
    """

    NAMESPACE = UUID(
        "8b0bd7dd-8118-4e8d-a51f-3a49da0c9377"
    )

    @classmethod
    def create(
        cls,
        *,
        document_id: UUID,
        source_key: str,
    ) -> UUID:
        if not isinstance(document_id, UUID):
            raise TypeError(
                "document_id deve ser um UUID."
            )

        if not isinstance(source_key, str):
            raise TypeError(
                "source_key deve ser uma string."
            )

        normalized_source_key = (
            source_key.strip().casefold()
        )

        if not normalized_source_key:
            raise ValueError(
                "source_key não pode ser vazio."
            )

        identity_key = (
            f"{document_id}:"
            f"{normalized_source_key}"
        )

        return uuid5(
            cls.NAMESPACE,
            identity_key,
        )

    @classmethod
    def document_sha256(
        cls,
        *,
        document_id: UUID,
    ) -> UUID:
        return cls.create(
            document_id=document_id,
            source_key="document:sha256",
        )

    @classmethod
    def image(
        cls,
        *,
        document_id: UUID,
        image_index: int,
    ) -> UUID:
        cls._validate_non_negative_index(
            image_index,
            field_name="image_index",
        )

        return cls.create(
            document_id=document_id,
            source_key=(
                f"image:{image_index}"
            ),
        )

    @classmethod
    def image_hash(
        cls,
        *,
        document_id: UUID,
        image_index: int,
        hash_type: str,
    ) -> UUID:
        cls._validate_non_negative_index(
            image_index,
            field_name="image_index",
        )

        normalized_hash_type = (
            cls._normalize_required_text(
                hash_type,
                field_name="hash_type",
            )
            .casefold()
        )

        return cls.create(
            document_id=document_id,
            source_key=(
                f"image:{image_index}:"
                f"hash:{normalized_hash_type}"
            ),
        )

    @classmethod
    def barcode(
        cls,
        *,
        document_id: UUID,
        barcode_index: int,
    ) -> UUID:
        cls._validate_non_negative_index(
            barcode_index,
            field_name="barcode_index",
        )

        return cls.create(
            document_id=document_id,
            source_key=(
                f"barcode:{barcode_index}"
            ),
        )

    @classmethod
    def qrcode(
        cls,
        *,
        document_id: UUID,
        qrcode_index: int,
    ) -> UUID:
        cls._validate_non_negative_index(
            qrcode_index,
            field_name="qrcode_index",
        )

        return cls.create(
            document_id=document_id,
            source_key=(
                f"qrcode:{qrcode_index}"
            ),
        )

    @classmethod
    def numeric_line(
        cls,
        *,
        document_id: UUID,
        line_index: int,
    ) -> UUID:
        """
        Gera a identidade da ocorrência bruta de uma linha numérica.
        """
        cls._validate_positive_index(
            line_index,
            field_name="line_index",
        )

        return cls.create(
            document_id=document_id,
            source_key=(
                f"numeric_line:{line_index}:raw"
            ),
        )

    @classmethod
    def normalized_numeric_line(
        cls,
        *,
        document_id: UUID,
        line_index: int,
    ) -> UUID:
        """
        Gera a identidade do valor normalizado derivado da ocorrência.
        """
        cls._validate_positive_index(
            line_index,
            field_name="line_index",
        )

        return cls.create(
            document_id=document_id,
            source_key=(
                f"numeric_line:{line_index}:normalized"
            ),
        )

    @classmethod
    def numeric_line_validation(
        cls,
        *,
        document_id: UUID,
        line_index: int,
    ) -> UUID:
        """
        Gera a identidade da validação estrutural da linha numérica.
        """
        cls._validate_positive_index(
            line_index,
            field_name="line_index",
        )

        return cls.create(
            document_id=document_id,
            source_key=(
                f"numeric_line:{line_index}:validation"
            ),
        )

    @classmethod
    def numeric_line_location(
        cls,
        *,
        document_id: UUID,
        line_index: int,
    ) -> UUID:
        """
        Gera a identidade da localização visual de uma linha numérica.
        """
        cls._validate_positive_index(
            line_index,
            field_name="line_index",
        )

        return cls.create(
            document_id=document_id,
            source_key=(
                f"numeric_line:{line_index}:location"
            ),
        )

    @staticmethod
    def _validate_non_negative_index(
        value: int,
        *,
        field_name: str,
    ) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
        ):
            raise TypeError(
                f"{field_name} deve ser um inteiro."
            )

        if value < 0:
            raise ValueError(
                f"{field_name} deve ser maior "
                "ou igual a zero."
            )

    @staticmethod
    def _validate_positive_index(
        value: int,
        *,
        field_name: str,
    ) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
        ):
            raise TypeError(
                f"{field_name} deve ser um inteiro."
            )

        if value < 1:
            raise ValueError(
                f"{field_name} deve ser maior "
                "ou igual a um."
            )

    @staticmethod
    def _normalize_required_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} deve ser uma string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} não pode ser vazio."
            )

        return normalized