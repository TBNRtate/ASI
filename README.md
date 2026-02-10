# ASI bootstrap

Python `src/asi` scaffold with packaging, dev tooling, CI, and guardrails.

## Quickstart

```bash
python -m pip install -e .[dev,memory]
make lint
make type
make test
PYTHONPATH=src python -m asi.interfaces.cli
```

## Memory backend

ASI supports two memory backends:

- `memory.backend: memory` → in-process volatile store.
- `memory.backend: sqlite` → persistent SQLite store with rebuildable vector index.

SQLite memory defaults under `./data/memory/` (gitignored), e.g. `./data/memory/memory.db`.

To reset memory, delete the DB (and optional index cache) under `./data/memory/`.
