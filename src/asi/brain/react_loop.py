from __future__ import annotations

import json
from typing import Any

from asi.llm.backend import LLMBackend, Message
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
    ) -> str:
        messages: list[Message] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        for _ in range(max_steps):
            raw = llm.generate(messages=messages, system_prompt=None)
            parsed = self._parse_response(raw)
            kind = parsed.get("type")

            if kind == "final":
                self.debug_trace = list(messages)
                return str(parsed.get("content", ""))

            if kind == "tool_call":
                tool_name = str(parsed.get("name", ""))
                args = parsed.get("args", {})
                if not isinstance(args, dict):
                    args = {}
                tool_result = tools.execute(tool_name, args)

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
        if parsed.get("type") == "final":
            return str(parsed.get("content", ""))
        return raw
