from pathlib import Path

from asi.safety.sandbox import Sandbox

ROOT = Path(__file__).resolve().parents[1]


def test_shell_true_appears_nowhere() -> None:
    for py in ROOT.rglob("*.py"):
        assert "shell" + "=True" not in py.read_text(), f"forbidden shell flag found in {py}"


def _config(workspace: Path) -> dict:
    return {
        "safety": {
            "sandbox": {
                "working_dir": str(workspace),
                "timeout_seconds": 20,
                "allowed_commands": ["ls", "cat", "grep", "find", "python", "git"],
                "blocked_tokens": [";", "|", "&", ">", "<", "$", "`"],
            },
            "dangerous_patterns": ["rm -rf", "mkfs", "dd if=", ":(){"],
        }
    }


def test_sandbox_blocks_dangerous_and_disallowed(tmp_path: Path) -> None:
    box = Sandbox(_config(tmp_path))

    blocked_rm = box.execute(["rm", "-rf", "/"])
    assert blocked_rm["blocked"]

    blocked_token = box.execute(["ls", ";", "rm", "-rf", "/"])
    assert blocked_token["blocked"]

    blocked_bash = box.execute(["bash", "-c", "echo hi"])
    assert blocked_bash["blocked"]


def test_sandbox_allows_ls(tmp_path: Path) -> None:
    (tmp_path / "ok.txt").write_text("ok")
    box = Sandbox(_config(tmp_path))
    result = box.execute(["ls"])
    assert result["success"]
    assert "ok.txt" in result["stdout"]
