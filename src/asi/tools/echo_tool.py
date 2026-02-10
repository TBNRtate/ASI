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
        "additionalProperties": False,
    }
    permission_level = "safe"

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        return {"echo": str(args["text"])}
