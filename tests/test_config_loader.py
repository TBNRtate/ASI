from pathlib import Path
from textwrap import dedent

import pytest

from asi.config import load_config
from asi.llm.factory import build_backend
from asi.llm.null_backend import NullBackend


def _write(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


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
          k_default: 3
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
    _write(tmp_path / "models.yaml", "models:\n  backend: llama_cpp\n")
    _write(tmp_path / "tools.yaml", "tools:\n  enabled_tools:\n    - shell\n")
    _write(tmp_path / "safety.yaml", "safety:\n  permission_mode: ask\n")
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

    # overlay precedence: default.yaml < models/tools/safety/prompts.yaml
    assert config["models"]["backend"] == "llama_cpp"
    assert config["safety"]["permission_mode"] == "ask"
    assert config["prompts"]["system_base"] == "overlay-base"
    assert config["tools"]["enabled_tools"] == ["shell"]

    # memory k should be available via k_default (and compat shim may also provide k)
    assert config["memory"]["k_default"] == 3


def test_missing_required_keys_raise_value_error(tmp_path: Path) -> None:
    # Provide all required config files, but intentionally omit required keys in default.yaml
    _write(
        tmp_path / "default.yaml",
        """
        models:
          backend: null_backend
        """,
    )
    _write(tmp_path / "models.yaml", "models:\n  backend: null_backend\n")
    _write(tmp_path / "tools.yaml", "tools:\n  enabled_tools: []\n")
    _write(tmp_path / "safety.yaml", "safety:\n  permission_mode: deny\n")
    _write(
        tmp_path / "prompts.yaml",
        """
        prompts:
          system_base: |
            hi
          tool_instructions: |
            ok
        """,
    )

    with pytest.raises(ValueError, match="Missing required config keys"):
        load_config(tmp_path)


def test_build_backend_returns_null_backend() -> None:
    backend = build_backend({"models": {"backend": "null_backend"}})
    assert isinstance(backend, NullBackend)

    out = backend.generate(messages=[{"role": "user", "content": "hello"}])
    assert out == '{"type": "final", "content": "NullBackend: hello"}'

