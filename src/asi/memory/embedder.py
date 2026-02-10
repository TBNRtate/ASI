from __future__ import annotations

import hashlib
from typing import Protocol


class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...


class HashEmbedder:
    def __init__(self, dim: int) -> None:
        if dim <= 0:
            raise ValueError("embedding dimension must be > 0")
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = text.split()
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = sum(v * v for v in vector) ** 0.5
        if norm == 0:
            return vector
        return [v / norm for v in vector]


class SentenceTransformerEmbedder:
    def __init__(self, dim: int) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "SentenceTransformerEmbedder is optional and not enabled in Task 5"
        )
