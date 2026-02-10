from pathlib import Path
from textwrap import dedent

import pytest

from asi.config import load_config
from asi.llm.factory import build_backend
from asi.llm.null_backend import NullBackend


def _write(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n")


def test_merge_order_overlays_default(tmp_path: Path) -> None:
    _write(
        tmp_path / "default.yaml",
        """
        models:
          backend: null_backend
        platform:
          acceleration: cpu
        agent:
          max_steps: 5
        memory:
          backend: memory
          k: 3
        safety:
          permission_mode: deny
        tools:
          enabled_tools: []
        prompts:
          system_base: |
            base
          tool_instructions: |
            base-tool
        """,
    )
    _write(tmp_path / "models.yaml", "models:\n  backend: llama_cpp")
    _write(tmp_path / "tools.yaml", "tools:\n  enabled_tools:\n    - shell")
    _write(tmp_path / "safety.yaml", "safety:\n  permission_mode: ask")
    _write(
        tmp_path / "prompts.yaml",
        """
        prompts:
          system_base: |
            overlay-base
          tool_instructions: |
            overlay-tools
          persona_default: |
            overlay-persona
        """,
    )

    config = load_config(tmp_path)
    assert config["models"]["backend"] == "llama_cpp"
    assert config["safety"]["permission_mode"] == "ask"
    assert config["prompts"]["system_base"] == "overlay-base"
    assert config["tools"]["enabled_tools"] == ["shell"]


def test_missing_required_keys_raise_value_error(tmp_path: Path) -> None:
    _write(tmp_path / "default.yaml", "models:\n  backend: null_backend")
    _write(tmp_path / "models.yaml", "models:\n  backend: null_backend")
    _write(tmp_path / "tools.yaml", "tools:\n  enabled_tools: []")
    _write(tmp_path / "safety.yaml", "safety:\n  permission_mode: deny")
    _write(tmp_path / "prompts.yaml", "prompts:\n  system_base: hi")

    with pytest.raises(ValueError, match="Missing required config keys"):
        load_config(tmp_path)


def test_build_backend_returns_null_backend() -> None:
    backend = build_backend({"models": {"backend": "null_backend"}})
    assert isinstance(backend, NullBackend)
    out = backend.generate(messages=[{"role": "user", "content": "hello"}])
    assert out == '{"type": "final", "content": "NullBackend: hello"}'
