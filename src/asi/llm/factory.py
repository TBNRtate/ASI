from __future__ import annotations

from typing import Any

from asi.llm.backend import LLMBackend
from asi.llm.null_backend import NullBackend


def build_backend(config: dict[str, Any]) -> LLMBackend:
    backend = str(config.get("models", {}).get("backend", "null_backend"))
    if backend in {"null", "null_backend"}:
        return NullBackend()
    if backend == "llama_cpp":
        raise NotImplementedError("llama_cpp backend not implemented yet")
    raise ValueError(f"Unsupported backend: {backend}")
