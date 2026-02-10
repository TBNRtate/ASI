from pathlib import Path

from asi.memory.store_sqlite import SQLiteMemoryStore


def _config(base: Path) -> dict:
    return {
        "memory": {
            "backend": "sqlite",
            "db_path": str(base / "memory.db"),
            "embedding_dim": 32,
            "index_path": str(base / "hnsw.index"),
            "max_elements": 1000,
            "ef_construction": 50,
            "M": 8,
            "ef_search": 20,
            "k_default": 3,
            "recency_half_life_days": 7,
        }
    }


def test_sqlite_memory_persists_and_rebuilds_index(tmp_path: Path) -> None:
    cfg = _config(tmp_path)

    store1 = SQLiteMemoryStore(cfg)
    store1.store({"type": "fact", "text": "alpha memory", "salience": 0.8})
    store1.store({"type": "fact", "text": "beta memory", "salience": 0.7})
    store1.store({"type": "fact", "text": "gamma memory", "salience": 0.6})

    first = store1.retrieve("alpha", k=2)
    assert first

    del store1

    store2 = SQLiteMemoryStore(cfg)
    assert store2.index_rebuilt
    second = store2.retrieve("alpha", k=2)

    assert second
    texts = [row["text"] for row in second]
    assert any("alpha" in t for t in texts)
