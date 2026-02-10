from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Protocol


class PermissionLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    SYSTEM = "system"
    NETWORK = "network"
    DELETE = "delete"


class PermissionPrompter(Protocol):
    def confirm(self, level: PermissionLevel, action_label: str | None = None) -> bool: ...


class DefaultDenyPrompter:
    def confirm(self, level: PermissionLevel, action_label: str | None = None) -> bool:
        _ = (level, action_label)
        return False


class PermissionManager:
    def __init__(
        self, config: Mapping[str, Any], prompter: PermissionPrompter | None = None
    ) -> None:
        self._config = config
        self._prompter = prompter or DefaultDenyPrompter()

    def is_allowed(self, level: PermissionLevel, action_label: str | None = None) -> bool:
        safety_cfg = self._config.get("safety", {})
        mode = (
            str(safety_cfg.get("permission_mode", "deny"))
            if isinstance(safety_cfg, Mapping)
            else "deny"
        )
        if mode == "deny":
            return level == PermissionLevel.READ
        if mode == "auto":
            return level in {PermissionLevel.READ, PermissionLevel.WRITE}
        if mode == "ask":
            if level in {PermissionLevel.READ, PermissionLevel.WRITE}:
                return True
            return self._prompter.confirm(level, action_label)
        return False
