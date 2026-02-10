from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from asi.brain.react_loop import ReActLoop
from asi.config import load_config
from asi.emotion.emotion_state import EmotionState
from asi.llm.factory import build_backend
from asi.memory.store import MemoryStore
from asi.memory.store_memory import MemoryStoreMemory
from asi.memory.store_sqlite import SQLiteMemoryStore
from asi.observability.ids import new_run_id
from asi.observability.logger import EventLogger
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
        self._memory: MemoryStore
        if memory_backend == "memory":
            self._memory = MemoryStoreMemory()
        elif memory_backend == "sqlite":
            self._memory = SQLiteMemoryStore(self._config)
        else:
            raise ValueError(f"Unsupported memory backend: {memory_backend}")

        self._logger: EventLogger | None = None
        if bool(self._config.get("observability", {}).get("enabled", False)):
            self._logger = EventLogger(self._config)

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

    def _build_system_prompt(
        self, session_id: str, user_message: str, run_id: str | None = None
    ) -> str:
        persona = self._persona.get_persona_context(session_id)
        memory_cfg = self._config.get("memory", {})
        k_default = int(memory_cfg.get("k_default", memory_cfg.get("k", 5)))

        start = time.perf_counter()
        snippets = self._memory.retrieve(query=user_message, k=k_default, session_id=session_id)
        if self._logger and run_id:
            self._logger.log(
                "memory_retrieve",
                run_id=run_id,
                session_id=session_id,
                data={
                    "k": k_default,
                    "results_count": len(snippets),
                    "duration_ms": (time.perf_counter() - start) * 1000,
                },
            )

        self._emotion.update(user_message=user_message, history=[])

        prompts = self._config.get("prompts", {})
        tool_names = ", ".join(self._tools.list_tool_names())
        parts = [
            str(prompts.get("system_base", "You are ASI.")),
            str(prompts.get("tool_instructions", "Always respond with valid JSON.")).replace(
                "{allowed_tools}", tool_names
            ),
            f"Persona: {persona['persona_name']}",
            f"Style: {persona['style_prompt']}",
            f"Emotion: {self._emotion.to_prompt_modifier()}",
            "Tools:\n" + self._tools.describe_tools(),
            f"Memory snippets: {snippets}",
        ]
        return "\n\n".join(parts)

    def respond(self, user_message: str, session_id: str, run_id: str | None = None) -> str:
        rid = run_id or new_run_id()
        system_prompt = self._build_system_prompt(
            session_id=session_id, user_message=user_message, run_id=rid
        )
        answer = self._react_loop.run(
            user_message=user_message,
            system_prompt=system_prompt,
            tools=self._tools,
            llm=self._llm,
            max_steps=int(self._config["agent"]["max_steps"]),
            run_id=rid,
            session_id=session_id,
            logger=self._logger,
        )
        self._memory.store(
            {
                "type": "episode",
                "text": f"USER: {user_message}\nASSISTANT: {answer}",
                "metadata": {
                    "session_id": session_id,
                    "run_id": rid,
                    "user": user_message,
                    "assistant": answer,
                },
            }
        )
        return answer
