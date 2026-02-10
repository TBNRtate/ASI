from __future__ import annotations

from typing import Any

from asi.memory.store import MemoryStore


class MemoryStoreMemory(MemoryStore):
    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def store(self, record: dict[str, Any]) -> int:
        self._records.append(record)
        return len(self._records)

    def retrieve(self, query: str, k: int, **filters: Any) -> list[dict[str, Any]]:
        _ = (query, filters)
        if k <= 0:
            return []
        return self._records[-k:]
