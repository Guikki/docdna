            "info": "Informativo",
        }

        return labels.get(
            normalized_severity,
            normalized_severity or "Não classificado",
        )

    def _translate_batch_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "pending": "Aguardando processamento",
            "processing": "Em processamento",
            "completed": "Concluído",
            "completed_with_errors": (
                "Concluído com ocorrências"
            ),
            "failed": "Falhou",
        }

        return labels.get(
            status,
            status,
        )

    def _translate_document_status(
        self,
        status: str,
    ) -> str:
        labels = {
            "pending": "Aguardando",
            "processing": "Em processamento",
            "completed": "Concluído",
            "failed": "Falhou",
        }

        return labels.get(
            status,
            status,
        )

    def _optional_uuid(
        self,
        value,
    ) -> str | None:
        if value is None:
            return None

        return str(value)

    def _safe_attribute(
        self,
        value: Any,
        attribute: str,
    ) -> Any:
        if value is None:
            return None

        if isinstance(value, dict):
            return value.get(
                attribute
            )

        return getattr(
            value,
            attribute,
            None,
        )

    def _enum_value(
        self,
        value: Any,
    ) -> Any:
        if value is None:
            return None

        return getattr(
            value,
            "value",
            value,
        )

    def _join_values(
        self,
        values: list[Any],
    ) -> str:
        normalized_values: list[str] = []

        for value in values:
            if value is None:
                continue

            normalized_value = str(
                value
            ).strip()

            if (
                not normalized_value
                or normalized_value
                in normalized_values
            ):
                continue

            normalized_values.append(
                normalized_value
            )

        return "\n".join(
            normalized_values
        )
