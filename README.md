# ASI bootstrap

Python `src/asi` scaffold with packaging, dev tooling, CI, and guardrails.

## Quickstart

```bash
python -m pip install -e .[dev]
make lint
make type
make test
```

## Memory backend

ASI supports two memory backends:

- `memory.backend: memory` → in-process volatile store.
- `memory.backend: sqlite` → persistent SQLite store with rebuildable vector index.

Default persistent paths are under `./data/` (gitignored), e.g. `./data/memory/memory.db`.

To reset persistent memory, delete the DB file (and optional index cache file) under `./data/memory/`.
