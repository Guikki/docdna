from uuid import UUID

from app.domain.models.batch import Batch


class BatchMemoryRepository:

    _batches: dict[UUID, Batch] = {}

    def save(self, batch: Batch) -> None:
        self._batches[batch.id] = batch

    def get_by_id(
        self,
        batch_id: UUID,
    ) -> Batch | None:
        return self._batches.get(batch_id)

    def list_all(self) -> list[Batch]:
        return list(self._batches.values())

    def delete(
        self,
        batch_id: UUID,
    ) -> bool:
        if batch_id not in self._batches:
            return False

        del self._batches[batch_id]
        return True