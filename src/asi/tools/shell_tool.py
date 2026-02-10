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
        "additionalProperties": False,
    }
    permission_level = "system"

    def __init__(self, sandbox: Sandbox) -> None:
        self._sandbox = sandbox

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._sandbox.execute(args["cmd"])
