from __future__ import annotations

from pathlib import Path
from typing import Any

from asi.brain.react_loop import ReActLoop
from asi.config import load_config
from asi.emotion.emotion_state import EmotionState
from asi.llm.factory import build_backend
from asi.memory.store_memory import MemoryStoreMemory
from asi.persona.persona_manager import PersonaManager
from asi.safety.permissions import PermissionManager
from asi.safety.sandbox import Sandbox
from asi.tools.echo_tool import EchoTool
from asi.tools.files_tool import FileReadTool, FileWriteTool
from asi.tools.registry import ToolRegistry
from asi.tools.shell_tool import ShellTool


class ArabellaBrain:
    def __init__(self, config_dir: str | Path) -> None:
        self._config = load_config(config_dir)
        self._llm = build_backend(self._config)
        self._persona = PersonaManager(self._config)
        self._emotion = EmotionState()

        memory_backend = str(self._config.get("memory", {}).get("backend", "memory"))
        if memory_backend in {"memory", "sqlite"}:
            self._memory = MemoryStoreMemory()
        else:
            raise ValueError(f"Unsupported memory backend: {memory_backend}")

        self._permission_manager = PermissionManager(self._config)
        self._sandbox = Sandbox(self._config)
        self._tools = ToolRegistry(permission_manager=self._permission_manager)

        enabled_tools = set(self._config.get("tools", {}).get("enabled_tools", []))
        read_roots = [
            Path(p)
            for p in self._config.get("tools", {})
            .get("file_access", {})
            .get("allowed_read_paths", ["./workspace"])
        ]
        write_roots = [
            Path(p)
            for p in self._config.get("tools", {})
            .get("file_access", {})
            .get("allowed_write_paths", ["./workspace"])
        ]

        self._tools.register(EchoTool())
        if "shell" in enabled_tools:
            self._tools.register(ShellTool(self._sandbox))
        if "file_read" in enabled_tools:
            self._tools.register(FileReadTool(read_roots))
        if "file_write" in enabled_tools:
            self._tools.register(FileWriteTool(write_roots))

        self._react_loop = ReActLoop()

    @property
    def memory_records(self) -> list[dict[str, Any]]:
        return list(self._memory.retrieve(query="", k=10_000))

    def _build_system_prompt(self, session_id: str, user_message: str) -> str:
        persona = self._persona.get_persona_context(session_id)
        snippets = self._memory.retrieve(
            query=user_message,
            k=int(self._config["memory"]["k"]),
            session_id=session_id,
        )

        self._emotion.update(user_message=user_message, history=[])

        prompts = self._config.get("prompts", {})
        parts = [
            str(prompts.get("system_base", "You are ASI.")),
            str(prompts.get("tool_instructions", "Always respond with valid JSON.")),
            f"Persona: {persona['persona_name']}",
            f"Style: {persona['style_prompt']}",
            f"Emotion: {self._emotion.to_prompt_modifier()}",
            "Tools:\n" + self._tools.describe_tools(),
            f"Memory snippets: {snippets}",
        ]
        return "\n\n".join(parts)

    def respond(self, user_message: str, session_id: str) -> str:
        system_prompt = self._build_system_prompt(session_id=session_id, user_message=user_message)
        answer = self._react_loop.run(
            user_message=user_message,
            system_prompt=system_prompt,
            tools=self._tools,
            llm=self._llm,
            max_steps=int(self._config["agent"]["max_steps"]),
        )
        self._memory.store(
            {
                "session_id": session_id,
                "user": user_message,
                "assistant": answer,
            }
        )
        return answer
