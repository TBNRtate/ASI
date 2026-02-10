from pathlib import Path
from textwrap import dedent

from asi.brain.arabella_brain import ArabellaBrain


def _write(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n")


def _write_config_dir(base: Path) -> None:
    _write(
        base / "default.yaml",
        """
        models:
          backend: null_backend
        platform:
          acceleration: cpu
        agent:
          max_steps: 4
        memory:
          backend: memory
          db_path: "./data/memory/memory.db"
          embedding_dim: 384
          k_default: 5
        safety:
          permission_mode: ask
          sandbox:
            working_dir: "./workspace"
            timeout_seconds: 20
            allowed_commands:
              - ls
            blocked_tokens:
              - ";"
          dangerous_patterns:
            - "rm -rf"
        tools:
          enabled_tools:
            - shell
            - file_read
            - file_write
          file_access:
            allowed_read_paths:
              - "./workspace"
            allowed_write_paths:
              - "./workspace"
        prompts:
          system_base: |
            Always respond with valid JSON.
          tool_instructions: |
            Use only listed tools.
          persona_default: |
            Be concise.
        """,
    )
    _write(base / "models.yaml", "models:\n  backend: null_backend")
    _write(
        base / "tools.yaml",
        """
        tools:
          enabled_tools:
            - shell
            - file_read
            - file_write
          file_access:
            allowed_read_paths:
              - "./workspace"
            allowed_write_paths:
              - "./workspace"
        """,
    )
    _write(
        base / "safety.yaml",
        """
        safety:
          permission_mode: ask
          sandbox:
            working_dir: "./workspace"
            timeout_seconds: 20
            allowed_commands:
              - ls
            blocked_tokens:
              - ";"
          dangerous_patterns:
            - "rm -rf"
        """,
    )
    _write(
        base / "prompts.yaml",
        """
        prompts:
          system_base: |
            Always respond with valid JSON.
          tool_instructions: |
            Use only listed tools.
          persona_default: |
            Be concise.
        """,
    )


def test_brain_respond_returns_string_and_stores_episode(tmp_path: Path) -> None:
    (tmp_path / "workspace").mkdir()
    _write_config_dir(tmp_path)
    brain = ArabellaBrain(config_dir=tmp_path)

    response = brain.respond("hello", session_id="s1")

    assert isinstance(response, str)
    assert response == "NullBackend: hello"
    records = brain.memory_records
    assert len(records) == 1
    assert "USER: hello" in records[0]["text"]
    assert "ASSISTANT: NullBackend: hello" in records[0]["text"]
