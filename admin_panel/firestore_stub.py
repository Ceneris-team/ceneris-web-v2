"""
Firestore stub used when you want to disable real Firestore access.
The stub implements a minimal API (collection(...).where(...).stream(),
document(...).get(), add(), delete(), etc.) so the application won't crash
when Firestore is disabled. It returns empty iterators or no-op results.
"""
from typing import Iterator, Any


class DocumentSnapshotStub:
    def __init__(self, id: str | None = None, data: dict | None = None, exists: bool = False):
        self.id = id
        self._data = data or {}
        self.exists = exists

    def to_dict(self) -> dict:
        return self._data


class DocumentRefStub:
    def __init__(self, id: str | None = None):
        self.id = id

    def get(self) -> DocumentSnapshotStub:
        return DocumentSnapshotStub(id=self.id, data={}, exists=False)

    def delete(self) -> None:
        return None

    def set(self, data: dict) -> None:
        return None

    def update(self, data: dict) -> None:
        return None


class CollectionRefStub:
    def __init__(self, name: str):
        self.name = name

    def order_by(self, *args, **kwargs) -> 'CollectionRefStub':
        return self

    def where(self, *args, **kwargs) -> 'CollectionRefStub':
        return self

    def stream(self) -> Iterator[DocumentSnapshotStub]:
        # Return an empty iterator so loops simply do nothing
        return iter(())

    def document(self, id: str | None = None) -> DocumentRefStub:
        return DocumentRefStub(id)

    def add(self, data: dict) -> tuple[DocumentRefStub, Any]:
        # Return a dummy DocumentRef and no write result
        return (DocumentRefStub('stub_id'), None)


class FirestoreStub:
    def collection(self, name: str) -> CollectionRefStub:
        return CollectionRefStub(name)

    def document(self, path: str) -> DocumentRefStub:
        return DocumentRefStub(path)


# Singleton instance used as `db` when Firestore is disabled
db = FirestoreStub()
