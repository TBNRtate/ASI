from __future__ import annotations

import json
from typing import Any, Callable

from asi.safety.guardrails import validate_tool_call
from asi.safety.permissions import PermissionLevel, PermissionManager
from asi.tools.base import Tool


class ToolRegistry:
    def __init__(
        self,
        permission_manager: PermissionManager,
        guardrail_fn: Callable[
            [str, dict[str, object]], tuple[bool, str, PermissionLevel]
        ] = validate_tool_call,
    ) -> None:
        self._tools: dict[str, Tool] = {}
        self._permission_manager = permission_manager
        self._guardrail_fn = guardrail_fn

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        ok, reason, level = self._guardrail_fn(name, args)
        if not ok:
            return {"success": False, "error": reason, "blocked": True}
        if not self._permission_manager.is_allowed(level, action_label=name):
            return {
                "success": False,
                "error": f"permission denied for {name}",
                "blocked": True,
            }
        if name not in self._tools:
            return {"success": False, "error": f"Unknown tool: {name}", "blocked": True}
        tool = self._tools[name]
        valid, message = tool.validate_args(args)
        if not valid:
            return {"success": False, "error": message, "blocked": True}
        try:
            result = tool.run(args)
            if "success" not in result:
                result["success"] = True
            if "blocked" not in result:
                result["blocked"] = False
            return result
        except Exception as exc:
            return {"success": False, "error": str(exc), "blocked": True}

    def describe_tools(self) -> str:
        if not self._tools:
            return "No tools enabled."
        lines: list[str] = []
        for tool in self._tools.values():
            schema = json.dumps(tool.parameters, sort_keys=True)
            lines.append(f"- {tool.name}: {tool.description} | schema={schema}")
        return "\n".join(lines)
