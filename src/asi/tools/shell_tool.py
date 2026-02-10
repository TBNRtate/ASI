from __future__ import annotations

from typing import Any

from asi.safety.sandbox import Sandbox
from asi.tools.base import Tool


class ShellTool(Tool):
    name = "shell"
    description = "Execute a restricted shell command in sandbox."
    parameters = {
        "type": "object",
        "properties": {
            "cmd": {"type": "array", "items": {"type": "string"}},
            "timeout": {"type": "number"},
        },
        "required": ["cmd"],
    }
    permission_level = "system"

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def validate_args(self, args: dict[str, Any]) -> tuple[bool, str]:
        if "cmd" not in args or not isinstance(args["cmd"], list):
            return False, "cmd must be an array of strings"
        if not all(isinstance(v, str) for v in args["cmd"]):
            return False, "cmd entries must be strings"
        return True, "ok"

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._sandbox.execute(args["cmd"])
