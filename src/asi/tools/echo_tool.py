from __future__ import annotations

from typing import Any

from asi.tools.base import Tool


class EchoTool(Tool):
    name = "echo"
    description = "Echoes provided text."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }
    permission_level = "safe"

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"echo": str(args["text"])}

    def validate_args(self, args: dict[str, Any]) -> tuple[bool, str]:
        if "text" not in args:
            return False, "missing required key: text"
        if not isinstance(args["text"], str):
            return False, "text must be a string"
        return True, "ok"
