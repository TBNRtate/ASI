from pathlib import Path

import pytest

from asi.tools.files_tool import FileReadTool, FileWriteTool


def test_file_read_and_traversal_block(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "ok.txt").write_text("hello")

    reader = FileReadTool([workspace])
    assert reader.run({"path": "ok.txt"})["content"] == "hello"

    with pytest.raises(ValueError):
        reader.run({"path": "../secrets.txt"})


def test_file_write_rejects_absolute_or_escape(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    writer = FileWriteTool([workspace])

    with pytest.raises(ValueError):
        writer.run({"path": "/etc/passwd", "content": "x"})

    with pytest.raises(ValueError):
        writer.run({"path": "../escape.txt", "content": "x"})


def test_symlink_escape_blocked(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("top-secret")
    (workspace / "link.txt").symlink_to(secret)

    reader = FileReadTool([workspace])
    with pytest.raises(ValueError):
        reader.run({"path": "link.txt"})
