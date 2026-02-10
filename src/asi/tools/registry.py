from __future__ import annotations

import json
import time
from typing import Any, Callable

from asi.observability.logger import EventLogger
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

    def execute(
        self,
        name: str,
        args: dict[str, Any],
        *,
        run_id: str | None = None,
        session_id: str | None = None,
        logger: EventLogger | None = None,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        if logger and run_id and session_id:
            logger.log(
                "tool_exec_start",
                run_id=run_id,
                session_id=session_id,
                data={"name": name, "args": args if logger.include_payloads else {}},
            )

        ok, reason, level = self._guardrail_fn(name, args)
        if not ok:
            result = {"success": False, "error": reason, "blocked": True}
            self._log_end(logger, run_id, session_id, name, result, start)
            return result
        if not self._permission_manager.is_allowed(level, action_label=name):
            result = {
                "success": False,
                "error": f"permission denied for {name}",
                "blocked": True,
            }
            self._log_end(logger, run_id, session_id, name, result, start)
            return result
        if name not in self._tools:
            result = {"success": False, "error": f"Unknown tool: {name}", "blocked": True}
            self._log_end(logger, run_id, session_id, name, result, start)
            return result
        tool = self._tools[name]
        valid, message = tool.validate_args(args)
        if not valid:
            result = {"success": False, "error": message, "blocked": True}
            self._log_end(logger, run_id, session_id, name, result, start)
            return result
        try:
            result = tool.run(args)
            if "success" not in result:
                result["success"] = True
            if "blocked" not in result:
                result["blocked"] = False
            self._log_end(logger, run_id, session_id, name, result, start)
            return result
        except Exception as exc:
            result = {"success": False, "error": str(exc), "blocked": True}
            self._log_end(logger, run_id, session_id, name, result, start)
            return result

    def _log_end(
        self,
        logger: EventLogger | None,
        run_id: str | None,
        session_id: str | None,
        name: str,
        result: dict[str, Any],
        started: float,
    ) -> None:
        if logger and run_id and session_id:
            logger.log(
                "tool_exec_end",
                run_id=run_id,
                session_id=session_id,
                data={
                    "name": name,
                    "duration_ms": (time.perf_counter() - started) * 1000,
                    "success": bool(result.get("success")),
                    "blocked": bool(result.get("blocked")),
                },
            )

    def describe_tools(self) -> str:
        if not self._tools:
            return "No tools enabled."
        lines: list[str] = []
        for tool in self._tools.values():
            schema = json.dumps(tool.parameters, sort_keys=True)
            lines.append(f"- {tool.name}: {tool.description} | schema={schema}")
        return "\n".join(lines)
