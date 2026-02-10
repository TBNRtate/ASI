from pathlib import Path
from textwrap import dedent

import pytest


def _write(path: Path, content: str) -> None:
    path.write_text(dedent(content).strip() + "\n")


def _write_config_dir(base: Path, log_dir: Path) -> None:
    _write(
        base / "default.yaml",
        f"""
        models:
          backend: null_backend
        platform:
          acceleration: cpu
        agent:
          max_steps: 4
        memory:
          backend: memory
          k_default: 3
        safety:
          permission_mode: deny
        tools:
          enabled_tools: []
        prompts:
          system_base: |
            Always respond with valid JSON.
          tool_instructions: |
            Use only listed tools.
        observability:
          enabled: true
          log_dir: "{log_dir}"
          rotate_daily: false
          include_payloads: true
          redact_secrets: true
        """,
    )
    _write(base / "models.yaml", "models:\n  backend: null_backend")
    _write(base / "tools.yaml", "tools:\n  enabled_tools: []")
    _write(base / "safety.yaml", "safety:\n  permission_mode: deny")
    _write(
        base / "prompts.yaml",
        """
        prompts:
          system_base: |
            Always respond with valid JSON.
          tool_instructions: |
            Use only listed tools.
        """,
    )


def test_health_and_chat_endpoints(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from asi.brain.arabella_brain import ArabellaBrain
    from asi.interfaces import api as api_module

    cfg = tmp_path / "cfg"
    cfg.mkdir()
    log_dir = tmp_path / "logs"
    _write_config_dir(cfg, log_dir)

    api_module.brain = ArabellaBrain(config_dir=cfg)
    assert api_module.app is not None
    client = TestClient(api_module.app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    resp = client.post("/chat", json={"session_id": "s1", "message": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "s1"
    assert isinstance(body["run_id"], str)
    assert isinstance(body["response"], str)

    log_file = log_dir / "events.jsonl"
    assert log_file.exists()
    assert len(log_file.read_text().splitlines()) >= 1
