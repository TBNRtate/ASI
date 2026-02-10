# ASI bootstrap

Python `src/asi` scaffold with packaging, dev tooling, CI, and guardrails.

## Quickstart

```bash
python -m pip install -e ".[dev,memory]"
make lint
make type
make test
PYTHONPATH=src python -m asi.interfaces.cli
