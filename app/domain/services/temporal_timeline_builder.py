from __future__ import annotations

from collections.abc import Iterable

from app.domain.models.detected_date import DetectedDate
from app.domain.models.temporal_timeline import TemporalTimeline


class TemporalTimelineBuilder:
    """
    Constrói uma TemporalTimeline a partir de datas detectadas.

    O builder organiza as observações temporais, mas não remove
    ocorrências repetidas e não avalia inconsistências.

    Duas datas iguais podem representar observações diferentes,
    provenientes de páginas, fontes ou campos distintos.
    """

    def build(
        self,
        *,
        document_id: str,
        detected_dates: Iterable[DetectedDate],
    ) -> TemporalTimeline:
        """
        Cria uma timeline imutável e cronologicamente ordenada.

        A ordenação considera:

        1. valor da data;
        2. número da página;
        3. origem da observação;
        4. campo de metadado;
        5. conteúdo original.

        Datas sem página, como metadados do PDF, são posicionadas
        antes das observações associadas às páginas quando possuem
        o mesmo valor.
        """

        normalized_document_id = document_id.strip()

        if not normalized_document_id:
            raise ValueError(
                "O identificador do documento não pode ser vazio."
            )

        dates = tuple(detected_dates)

        self._validate_document_ids(
            document_id=normalized_document_id,
            detected_dates=dates,
        )

        ordered_dates = tuple(
            sorted(
                dates,
                key=self._sorting_key,
            )
        )

        return TemporalTimeline(
            document_id=normalized_document_id,
            dates=ordered_dates,
        )

    def _validate_document_ids(
        self,
        *,
        document_id: str,
        detected_dates: tuple[DetectedDate, ...],
    ) -> None:
        """
        Impede que uma timeline documental contenha datas
        pertencentes a documentos diferentes.
        """

        invalid_dates = tuple(
            detected_date
            for detected_date in detected_dates
            if detected_date.document_id != document_id
        )

        if not invalid_dates:
            return

        invalid_document_ids = sorted(
            {
                detected_date.document_id
                for detected_date in invalid_dates
            }
        )

        invalid_ids = ", ".join(invalid_document_ids)

        raise ValueError(
            "Não é possível construir uma timeline com datas "
            "de documentos diferentes. "
            f"Documento esperado: {document_id}. "
            f"Documentos encontrados: {invalid_ids}."
        )

    def _sorting_key(
        self,
        detected_date: DetectedDate,
    ) -> tuple:
        """
        Produz uma chave estável para a ordenação das datas.

        O uso de valores auxiliares evita comparações entre None
        e valores concretos durante a ordenação.
        """

        page_number = (
            detected_date.page_number
            if detected_date.page_number is not None
            else -1
        )

        metadata_field = detected_date.metadata_field or ""
        raw_content = detected_date.raw_content or ""

        return (
            detected_date.value,
            page_number,
            detected_date.source.value,
            metadata_field,
            raw_content,
        )