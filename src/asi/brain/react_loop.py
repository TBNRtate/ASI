from __future__ import annotations

import json
import time
from typing import Any

from asi.llm.backend import LLMBackend, Message
from asi.observability.logger import EventLogger
from asi.tools.registry import ToolRegistry


class ReActLoop:
    def __init__(self) -> None:
        self.debug_trace: list[Message] = []

    def _parse_response(self, raw: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"type": "final", "content": raw}
        if not isinstance(parsed, dict):
            return {"type": "final", "content": raw}
        return parsed

    def run(
        self,
        user_message: str,
        system_prompt: str,
        tools: ToolRegistry,
        llm: LLMBackend,
        max_steps: int,
        run_id: str,
        session_id: str,
        logger: EventLogger | None = None,
    ) -> str:
        started = time.perf_counter()
        messages: list[Message] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        if logger:
            logger.log(
                "react_start",
                run_id=run_id,
                session_id=session_id,
                data={"max_steps": max_steps, "message_len": len(user_message)},
            )

        for step in range(max_steps):
            raw = llm.generate(messages=messages, system_prompt=None)
            if logger:
                logger.log(
                    "llm_output",
                    run_id=run_id,
                    session_id=session_id,
                    data={"step": step, "raw_output": raw if logger.include_payloads else ""},
                )
            parsed = self._parse_response(raw)
            kind = parsed.get("type")

            if kind == "final":
                self.debug_trace = list(messages)
                result = str(parsed.get("content", ""))
                if logger:
                    logger.log(
                        "react_final",
                        run_id=run_id,
                        session_id=session_id,
                        data={
                            "steps_used": step + 1,
                            "latency_ms": (time.perf_counter() - started) * 1000,
                        },
                    )
                return result

            if kind == "tool_call":
                tool_name = str(parsed.get("name", ""))
                args = parsed.get("args", {})
                if not isinstance(args, dict):
                    args = {}
                if logger:
                    logger.log(
                        "tool_call",
                        run_id=run_id,
                        session_id=session_id,
                        data={"name": tool_name, "args": args if logger.include_payloads else {}},
                    )
                tool_started = time.perf_counter()
                tool_result = tools.execute(
                    tool_name,
                    args,
                    run_id=run_id,
                    session_id=session_id,
                    logger=logger,
                )
                if logger:
                    logger.log(
                        "tool_result",
                        run_id=run_id,
                        session_id=session_id,
                        data={
                            "name": tool_name,
                            "success": bool(tool_result.get("success")),
                            "blocked": bool(tool_result.get("blocked")),
                            "duration_ms": (time.perf_counter() - tool_started) * 1000,
                        },
                    )

                messages.append({"role": "assistant", "content": json.dumps(parsed)})
                if tool_result.get("blocked"):
                    reason = str(tool_result.get("error", "blocked"))
                    messages.append({"role": "user", "content": f"[tool_blocked] reason={reason}"})
                else:
                    messages.append(
                        {
                            "role": "user",
                            "content": f"[tool_result] {json.dumps(tool_result, sort_keys=True)}",
                        }
                    )
                continue

            self.debug_trace = list(messages)
            return str(parsed)

        messages.append({"role": "user", "content": "Respond with a final answer JSON."})
        raw = llm.generate(messages=messages, system_prompt=None)
        parsed = self._parse_response(raw)
        self.debug_trace = list(messages)
        result = str(parsed.get("content", "")) if parsed.get("type") == "final" else raw
        if logger:
            logger.log(
                "react_final",
                run_id=run_id,
                session_id=session_id,
                data={
                    "steps_used": max_steps,
                    "latency_ms": (time.perf_counter() - started) * 1000,
                },
            )
        return result
