from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(
    frozen=True,
    slots=True,
)
class BarcodeNumericLineDocumentCandidate:
    """
    Reúne as ocorrências de código de barras e linhas numéricas
    pertencentes a um único documento dentro de um grupo candidato.

    Os IDs das ocorrências são preservados mesmo quando os valores
    normalizados se repetem.
    """

    document_id: UUID
    barcode_element_ids: tuple[UUID, ...]
    numeric_line_element_ids: tuple[UUID, ...]
    numeric_line_values: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.document_id,
            UUID,
        ):
            raise TypeError(
                "document_id deve ser um UUID."
            )

        if not self.barcode_element_ids:
            raise ValueError(
                "O documento candidato deve possuir "
                "ao menos um elemento de código de barras."
            )

        self._validate_uuid_tuple(
            self.barcode_element_ids,
            field_name="barcode_element_ids",
        )

        self._validate_uuid_tuple(
            self.numeric_line_element_ids,
            field_name="numeric_line_element_ids",
        )

        self._validate_numeric_line_values(
            self.numeric_line_values
        )

    @property
    def has_numeric_lines(self) -> bool:
        return bool(
            self.numeric_line_values
        )

    @staticmethod
    def _validate_uuid_tuple(
        values: tuple[UUID, ...],
        *,
        field_name: str,
    ) -> None:
        if not isinstance(
            values,
            tuple,
        ):
            raise TypeError(
                f"{field_name} deve ser uma tupla."
            )

        for value in values:
            if not isinstance(
                value,
                UUID,
            ):
                raise TypeError(
                    f"{field_name} deve conter "
                    "somente UUIDs."
                )

        if len(
            set(values)
        ) != len(values):
            raise ValueError(
                f"{field_name} não pode conter "
                "IDs repetidos."
            )

    @staticmethod
    def _validate_numeric_line_values(
        values: tuple[str, ...],
    ) -> None:
        if not isinstance(
            values,
            tuple,
        ):
            raise TypeError(
                "numeric_line_values deve ser uma tupla."
            )

        for value in values:
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    "numeric_line_values deve conter "
                    "somente strings."
                )

            if not value.strip():
                raise ValueError(
                    "numeric_line_values deve conter "
                    "somente strings não vazias."
                )

        if len(
            set(values)
        ) != len(values):
            raise ValueError(
                "numeric_line_values não pode "
                "conter valores repetidos."
            )


@dataclass(
    frozen=True,
    slots=True,
)
class BarcodeNumericLineCandidateGroup:
    """
    Representa um grupo de documentos que compartilham o mesmo
    código de barras, mas apresentam conjuntos distintos de linhas
    numéricas normalizadas.

    O grupo preserva as ocorrências sem materializar pares entre
    documentos.
    """

    source_index: str
    barcode_key: str
    documents: tuple[
        BarcodeNumericLineDocumentCandidate,
        ...
    ]
    represented_barcode_relations: int

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_index,
            str,
        ):
            raise TypeError(
                "source_index deve ser uma string."
            )

        normalized_source_index = (
            self.source_index.strip()
        )

        if not normalized_source_index:
            raise ValueError(
                "source_index não pode ser vazio."
            )

        object.__setattr__(
            self,
            "source_index",
            normalized_source_index,
        )

        if not isinstance(
            self.barcode_key,
            str,
        ):
            raise TypeError(
                "barcode_key deve ser uma string."
            )

        normalized_barcode_key = (
            self.barcode_key.strip()
        )

        if not normalized_barcode_key:
            raise ValueError(
                "barcode_key não pode ser vazio."
            )

        object.__setattr__(
            self,
            "barcode_key",
            normalized_barcode_key,
        )

        if not isinstance(
            self.documents,
            tuple,
        ):
            raise TypeError(
                "documents deve ser uma tupla."
            )

        if len(
            self.documents
        ) < 2:
            raise ValueError(
                "Um grupo candidato deve possuir "
                "ao menos dois documentos."
            )

        for document in self.documents:
            if not isinstance(
                document,
                BarcodeNumericLineDocumentCandidate,
            ):
                raise TypeError(
                    "documents deve conter somente "
                    "BarcodeNumericLineDocumentCandidate."
                )

        document_ids = [
            document.document_id
            for document
            in self.documents
        ]

        if len(
            set(document_ids)
        ) != len(document_ids):
            raise ValueError(
                "documents não pode conter "
                "documentos repetidos."
            )

        if (
            not isinstance(
                self.represented_barcode_relations,
                int,
            )
            or isinstance(
                self.represented_barcode_relations,
                bool,
            )
        ):
            raise TypeError(
                "represented_barcode_relations "
                "deve ser um inteiro."
            )

        if (
            self.represented_barcode_relations
            < 1
        ):
            raise ValueError(
                "represented_barcode_relations "
                "deve ser maior ou igual a um."
            )

        if not self.has_divergence:
            raise ValueError(
                "O grupo candidato deve possuir "
                "divergência entre linhas numéricas."
            )

    @property
    def document_ids(
        self,
    ) -> tuple[UUID, ...]:
        return tuple(
            document.document_id
            for document
            in self.documents
        )

    @property
    def document_count(self) -> int:
        return len(
            self.documents
        )

    @property
    def documents_with_numeric_lines(
        self,
    ) -> int:
        return sum(
            document.has_numeric_lines
            for document
            in self.documents
        )

    @property
    def barcode_element_ids(
        self,
    ) -> tuple[UUID, ...]:
        return tuple(
            element_id
            for document
            in self.documents
            for element_id
            in document.barcode_element_ids
        )

    @property
    def numeric_line_element_ids(
        self,
    ) -> tuple[UUID, ...]:
        return tuple(
            element_id
            for document
            in self.documents
            for element_id
            in document.numeric_line_element_ids
        )

    @property
    def distinct_numeric_line_values(
        self,
    ) -> tuple[str, ...]:
        values: list[str] = []
        seen: set[str] = set()

        for document in self.documents:
            for value in (
                document.numeric_line_values
            ):
                if value in seen:
                    continue

                seen.add(
                    value
                )

                values.append(
                    value
                )

        return tuple(
            values
        )

    @property
    def has_divergence(self) -> bool:
        """
        Determina se existem conjuntos distintos de linhas numéricas
        entre os documentos que possuem linhas detectadas.

        Repetições da mesma linha dentro do mesmo documento não geram
        divergência.

        A ordem em que as linhas foram encontradas também não altera
        o resultado.
        """
        signatures = {
            frozenset(
                document.numeric_line_values
            )
            for document
            in self.documents
            if document.has_numeric_lines
        }

        return (
            len(signatures) >= 2
        )