from __future__ import annotations

import json
import time
from typing import Any

from asi.brain.protocol import ProtocolError, parse_model_output
from asi.llm.backend import LLMBackend, Message
from asi.observability.logger import EventLogger
from asi.tools.registry import ToolRegistry


class ReActLoop:
    def __init__(self) -> None:
        self.debug_trace: list[Message] = []

    def _execute_tool_call(
        self,
        call: dict[str, Any],
        messages: list[Message],
        tools: ToolRegistry,
        run_id: str,
        session_id: str,
        logger: EventLogger | None,
    ) -> None:
        tool_name = str(call.get("name", ""))
        args = call.get("args", {})
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

        messages.append({"role": "assistant", "content": json.dumps(call, sort_keys=True)})
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

        repaired = False
        fallback_text = "Sorry, I couldn't produce a valid tool protocol response."

        for step in range(max_steps):
            raw = llm.generate(messages=messages, system_prompt=None)
            if logger:
                logger.log(
                    "llm_output",
                    run_id=run_id,
                    session_id=session_id,
                    data={"step": step, "raw_output": raw if logger.include_payloads else ""},
                )
            try:
                parsed = parse_model_output(raw)
            except ProtocolError as exc:
                if logger:
                    logger.log(
                        "protocol_error",
                        run_id=run_id,
                        session_id=session_id,
                        data={"reason": str(exc), "step": step},
                    )
                if repaired:
                    self.debug_trace = list(messages)
                    return (
                        "I couldn't format a valid tool request. "
                        f"Here's my best answer without tools: {fallback_text}"
                    )
                repaired = True
                fallback_text = raw
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your last response was invalid. Respond again with ONLY valid JSON "
                            "following protocol type final/tool_call/tool_calls."
                        ),
                    }
                )
                continue

            kind = parsed["type"]
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
                self._execute_tool_call(parsed, messages, tools, run_id, session_id, logger)
                continue

            if kind == "tool_calls":
                calls = parsed["calls"]
                for call in calls:
                    self._execute_tool_call(call, messages, tools, run_id, session_id, logger)
                continue

        messages.append({"role": "user", "content": "Respond with a final answer JSON."})
        raw = llm.generate(messages=messages, system_prompt=None)
        try:
            parsed = parse_model_output(raw)
            result = (
                str(parsed.get("content", "")) if parsed.get("type") == "final" else fallback_text
            )
        except ProtocolError:
            result = fallback_text

        self.debug_trace = list(messages)
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
