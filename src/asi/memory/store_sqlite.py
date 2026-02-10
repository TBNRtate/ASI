from __future__ import annotations

import json
import math
import sqlite3
import struct
import time
from pathlib import Path
from typing import Any

from asi.memory.embedder import Embedder, HashEmbedder
from asi.memory.store import MemoryStore
from asi.memory.vector_index import HNSWVectorIndex


class SQLiteMemoryStore(MemoryStore):
    def __init__(self, config: dict[str, Any], embedder: Embedder | None = None) -> None:
        memory_cfg = config.get("memory", {})
        self._db_path = Path(str(memory_cfg.get("db_path", "./data/memory/memory.db")))
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._dim = int(memory_cfg.get("embedding_dim", 384))
        self._embedder: Embedder = embedder or HashEmbedder(dim=self._dim)
        self._half_life_days = float(memory_cfg.get("recency_half_life_days", 7))

        self._index = HNSWVectorIndex(
            dim=self._dim,
            max_elements=int(memory_cfg.get("max_elements", 50_000)),
            ef_construction=int(memory_cfg.get("ef_construction", 200)),
            m=int(memory_cfg.get("M", 16)),
            ef_search=int(memory_cfg.get("ef_search", 50)),
        )

        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._rebuild_index_from_db()

    @property
    def index_rebuilt(self) -> bool:
        return self._index.rebuilt_from_db

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                type TEXT,
                text TEXT NOT NULL,
                created_at REAL NOT NULL,
                salience REAL DEFAULT 0.5,
                valence REAL DEFAULT 0.0,
                metadata TEXT,
                embedding BLOB
            )
            """
        )
        self._conn.commit()

    def _pack_embedding(self, emb: list[float]) -> bytes:
        return struct.pack(f"<{len(emb)}f", *emb)

    def _unpack_embedding(self, blob: bytes) -> list[float]:
        if not blob:
            return [0.0] * self._dim
        count = len(blob) // 4
        values = struct.unpack(f"<{count}f", blob)
        return [float(x) for x in values]

    def _rebuild_index_from_db(self) -> None:
        rows = self._conn.execute(
            "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL"
        ).fetchall()
        pairs: list[tuple[int, list[float]]] = []
        for row in rows:
            pairs.append((int(row["id"]), self._unpack_embedding(row["embedding"])))
        self._index.build_from_db(pairs)

    def store(self, record: dict[str, Any]) -> int:
        text = str(record.get("text") or record.get("content") or "")
        if not text:
            raise ValueError("memory record requires non-empty text/content")
        created_at = float(record.get("created_at", time.time()))
        salience = float(record.get("salience", 0.5))
        valence = float(record.get("valence", 0.0))
        memory_type = str(record.get("type", "episode"))
        metadata = record.get("metadata", {})
        metadata_json = json.dumps(metadata, sort_keys=True)

        embedding = self._embedder.embed(text)
        if len(embedding) != self._dim:
            raise ValueError("embedder output dimension mismatch")
        emb_blob = self._pack_embedding(embedding)

        cur = self._conn.execute(
            """
            INSERT INTO memories (type, text, created_at, salience, valence, metadata, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (memory_type, text, created_at, salience, valence, metadata_json, emb_blob),
        )
        self._conn.commit()
        row_id = cur.lastrowid
        assert row_id is not None
        memory_id = int(row_id)
        self._index.add(memory_id, embedding)
        return memory_id

    def retrieve(self, query: str, k: int, **filters: Any) -> list[dict[str, Any]]:
        if k <= 0:
            return []
        query_embedding = self._embedder.embed(query)
        candidate_ids = self._index.search(query_embedding, k=max(k * 3, k))
        if not candidate_ids:
            return []

        placeholders = ",".join(["?"] * len(candidate_ids))
        sql = (
            "SELECT id, type, text, created_at, salience, valence, metadata "
            f"FROM memories WHERE id IN ({placeholders})"
        )
        rows = self._conn.execute(sql, tuple(candidate_ids)).fetchall()

        now = time.time()
        target_valence = filters.get("valence")
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            age_days = max((now - float(row["created_at"])) / 86_400.0, 0.0)
            recency = math.exp(-math.log(2) * age_days / max(self._half_life_days, 0.1))
            salience = float(row["salience"])
            valence_bonus = 0.0
            if target_valence is not None:
                valence_bonus = 1.0 - min(abs(float(target_valence) - float(row["valence"])), 1.0)
            score = (salience * 0.65) + (recency * 0.3) + (valence_bonus * 0.05)
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        out: list[dict[str, Any]] = []
        for _, row in scored[:k]:
            out.append(
                {
                    "id": int(row["id"]),
                    "type": str(row["type"]),
                    "text": str(row["text"]),
                    "created_at": float(row["created_at"]),
                    "salience": float(row["salience"]),
                    "valence": float(row["valence"]),
                    "metadata": json.loads(str(row["metadata"] or "{}")),
                }
            )
        return out
