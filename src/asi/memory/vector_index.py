from __future__ import annotations

from typing import Iterable

try:
    import hnswlib  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency fallback
    hnswlib = None


class HNSWVectorIndex:
    def __init__(
        self,
        dim: int,
        max_elements: int,
        ef_construction: int,
        m: int,
        ef_search: int,
    ) -> None:
        self._dim = dim
        self._max_elements = max_elements
        self._ef_construction = ef_construction
        self._m = m
        self._ef_search = ef_search
        self._embeddings: dict[int, list[float]] = {}
        self._index = None
        if hnswlib is not None:
            index = hnswlib.Index(space="cosine", dim=dim)
            index.init_index(max_elements=max_elements, ef_construction=ef_construction, M=m)
            index.set_ef(ef_search)
            self._index = index
        self.rebuilt_from_db = False

    def build_from_db(self, rows: Iterable[tuple[int, list[float]]]) -> None:
        self._embeddings.clear()
        pairs = list(rows)
        for memory_id, emb in pairs:
            self._embeddings[memory_id] = emb

        if self._index is not None:
            if pairs:
                self._index.add_items([emb for _, emb in pairs], [mid for mid, _ in pairs])
        self.rebuilt_from_db = True

    def add(self, memory_id: int, embedding: list[float]) -> None:
        self._embeddings[memory_id] = embedding
        if self._index is not None:
            self._index.add_items([embedding], [memory_id])

    def search(self, query_embedding: list[float], k: int) -> list[int]:
        if k <= 0 or not self._embeddings:
            return []
        if self._index is not None:
            labels, _ = self._index.knn_query(query_embedding, k=min(k, len(self._embeddings)))
            return [int(x) for x in labels[0]]

        # Brute-force cosine similarity fallback when hnswlib is unavailable.
        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5
            nb = sum(y * y for y in b) ** 0.5
            if na == 0 or nb == 0:
                return -1.0
            return float(dot / (na * nb))

        ranked = sorted(
            self._embeddings.items(),
            key=lambda item: cosine(query_embedding, item[1]),
            reverse=True,
        )
        return [memory_id for memory_id, _ in ranked[:k]]
