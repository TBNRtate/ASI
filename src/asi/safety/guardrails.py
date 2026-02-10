from __future__ import annotations

from asi.safety.permissions import PermissionLevel


def validate_tool_call(name: str, args: dict[str, object]) -> tuple[bool, str, PermissionLevel]:
    _ = args
    mapping = {
        "shell": PermissionLevel.SYSTEM,
        "file_read": PermissionLevel.READ,
        "file_write": PermissionLevel.WRITE,
        "echo": PermissionLevel.READ,
    }
    if name not in mapping:
        return False, f"unknown tool: {name}", PermissionLevel.SYSTEM
    return True, "ok", mapping[name]
