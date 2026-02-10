from __future__ import annotations

from pathlib import Path
from typing import Any

from asi.safety.paths import is_path_allowed, resolve_safe_path
from asi.tools.base import Tool


class _FileToolBase(Tool):
    def __init__(self, allowed_roots: list[Path]) -> None:
        self._allowed_roots = [p.resolve() for p in allowed_roots]

    def _resolve(self, user_path: str) -> Path:
        if Path(user_path).is_absolute():
            raise ValueError("absolute paths are not allowed")
        for root in self._allowed_roots:
            try:
                resolved = resolve_safe_path(root, user_path)
            except ValueError:
                continue
            if is_path_allowed(resolved, self._allowed_roots):
                return resolved
        raise ValueError("path is outside allowed roots")


class FileReadTool(_FileToolBase):
    name = "file_read"
    description = "Read text from an allowed file path."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    permission_level = "read"

    def validate_args(self, args: dict[str, Any]) -> tuple[bool, str]:
        if "path" not in args or not isinstance(args["path"], str):
            return False, "path must be a string"
        return True, "ok"

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(args["path"])
        return {"content": path.read_text()}


class FileWriteTool(_FileToolBase):
    name = "file_write"
    description = "Write text content to an allowed file path."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }
    permission_level = "write"

    def validate_args(self, args: dict[str, Any]) -> tuple[bool, str]:
        if "path" not in args or not isinstance(args["path"], str):
            return False, "path must be a string"
        if "content" not in args or not isinstance(args["content"], str):
            return False, "content must be a string"
        return True, "ok"

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        data = args["content"]
        path.write_text(data)
        return {"written": True, "bytes": len(data.encode("utf-8"))}
