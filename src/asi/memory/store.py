from __future__ import annotations

from typing import Any, Protocol


class MemoryStore(Protocol):
    def store(self, record: dict[str, Any]) -> int: ...

    def retrieve(self, query: str, k: int, **filters: Any) -> list[dict[str, Any]]: ...
