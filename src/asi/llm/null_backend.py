from __future__ import annotations

import json
from typing import Iterator

from asi.llm.backend import Message


class NullBackend:
    def generate(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> str:
        _ = (system_prompt, kwargs)
        user_messages = [m["content"] for m in messages if m["role"] == "user"]
        last_user = user_messages[-1] if user_messages else ""

        if last_user.startswith("[tool_blocked]"):
            return json.dumps({"type": "final", "content": "Tool blocked; proceeding safely."})

        if last_user.startswith("[tool_result]"):
            payload = last_user.removeprefix("[tool_result]").strip()
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                parsed = {"echo": ""}
            if "echo" in parsed:
                return json.dumps(
                    {"type": "final", "content": f"Tool returned: {parsed.get('echo', '')}"}
                )
            if parsed.get("written"):
                return json.dumps({"type": "final", "content": "Write completed."})
            if "content" in parsed:
                return json.dumps({"type": "final", "content": f"Read: {parsed['content']}"})
            return json.dumps({"type": "final", "content": "Tool completed."})

        lowered = last_user.lower()
        if "use_tool" in lowered:
            return json.dumps({"type": "tool_call", "name": "echo", "args": {"text": "hi"}})
        if "file_write" in lowered:
            return json.dumps(
                {
                    "type": "tool_call",
                    "name": "file_write",
                    "args": {"path": "demo.txt", "content": "hello from tool"},
                }
            )
        if "file_read" in lowered:
            return json.dumps(
                {
                    "type": "tool_call",
                    "name": "file_read",
                    "args": {"path": "demo.txt"},
                }
            )
        if "shell_block" in lowered:
            return json.dumps(
                {
                    "type": "tool_call",
                    "name": "shell",
                    "args": {"cmd": ["bash", "-c", "echo hi"]},
                }
            )

        return json.dumps({"type": "final", "content": f"NullBackend: {last_user}"})

    def stream_generate(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> Iterator[str]:
        yield self.generate(messages=messages, system_prompt=system_prompt, **kwargs)

    def tokenize(self, text: str) -> list[int]:
        return [i for i, _ in enumerate(text.split(), start=1)]

    def count_tokens(self, text: str) -> int:
        return len(self.tokenize(text))
