from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _parse_scalar(raw: str) -> Any:
    value = raw.strip().strip('"')
    if value == "[]":
        return []
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    return value


def _load_simple_yaml(path: Path) -> dict[str, Any]:
    lines = path.read_text().splitlines()
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    i = 0

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.rstrip()
        i += 1
        if not line or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if stripped.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Invalid YAML list context in {path}: {raw_line}")
            parent.append(_parse_scalar(stripped[2:]))
            continue

        key, sep, remainder = stripped.partition(":")
        if not sep:
            raise ValueError(f"Invalid YAML line in {path}: {raw_line}")
        value_text = remainder.strip()

        if value_text == "|":
            block_lines: list[str] = []
            while i < len(lines):
                next_line = lines[i]
                if not next_line.strip():
                    block_lines.append("")
                    i += 1
                    continue
                next_indent = len(next_line) - len(next_line.lstrip(" "))
                if next_indent <= indent:
                    break
                block_lines.append(next_line[indent + 2 :])
                i += 1
            if not isinstance(parent, dict):
                raise ValueError(f"Invalid YAML mapping context in {path}: {raw_line}")
            parent[key] = "\n".join(block_lines).strip()
            continue

        if not isinstance(parent, dict):
            raise ValueError(f"Invalid YAML structure in {path}: {raw_line}")

        if value_text == "":
            node: Any = {}
            j = i
            while j < len(lines):
                probe = lines[j]
                if not probe.strip() or probe.lstrip().startswith("#"):
                    j += 1
                    continue
                probe_indent = len(probe) - len(probe.lstrip(" "))
                if probe_indent <= indent:
                    break
                node = [] if probe.strip().startswith("- ") else {}
                break
            parent[key] = node
            stack.append((indent, node))
        else:
            parent[key] = _parse_scalar(value_text)

    return root


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    env_map = {
        "ASI_MODELS_BACKEND": ("models", "backend"),
        "ASI_PLATFORM_ACCELERATION": ("platform", "acceleration"),
        "ASI_AGENT_MAX_STEPS": ("agent", "max_steps"),
        "ASI_MEMORY_K_DEFAULT": ("memory", "k_default"),
        "ASI_MEMORY_BACKEND": ("memory", "backend"),
        "ASI_SAFETY_PERMISSION_MODE": ("safety", "permission_mode"),
    }
    updated = dict(config)
    for env_key, path in env_map.items():
        if env_key not in os.environ:
            continue
        cursor = updated
        for part in path[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[path[-1]] = _parse_scalar(os.environ[env_key])
    return updated


def _validate(config: dict[str, Any]) -> None:
    required = [
        ("models", "backend"),
        ("platform", "acceleration"),
        ("agent", "max_steps"),
        ("memory", "backend"),
        ("memory", "db_path"),
        ("memory", "embedding_dim"),
        ("memory", "k_default"),
        ("safety", "permission_mode"),
        ("tools", "enabled_tools"),
        ("prompts", "system_base"),
        ("prompts", "tool_instructions"),
    ]
    missing: list[str] = []
    for path in required:
        cursor: Any = config
        valid = True
        for part in path:
            if not isinstance(cursor, dict) or part not in cursor:
                valid = False
                break
            cursor = cursor[part]
        if not valid:
            missing.append(".".join(path))
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")

    if config["models"]["backend"] not in {"llama_cpp", "null_backend", "null"}:
        raise ValueError("models.backend must be one of: llama_cpp, null_backend, null")
    if config["platform"]["acceleration"] not in {"cpu", "metal"}:
        raise ValueError("platform.acceleration must be one of: cpu, metal")
    if config["safety"]["permission_mode"] not in {"deny", "auto", "ask"}:
        raise ValueError("safety.permission_mode must be one of: deny, auto, ask")
    if config["memory"]["backend"] not in {"memory", "sqlite"}:
        raise ValueError("memory.backend must be one of: memory, sqlite")


def load_config(config_dir: Path | str) -> dict[str, Any]:
    root = Path(config_dir)
    order = ["default.yaml", "models.yaml", "tools.yaml", "safety.yaml", "prompts.yaml"]

    merged: dict[str, Any] = {}
    for name in order:
        file_path = root / name
        if not file_path.exists():
            raise ValueError(f"Missing required config file: {file_path}")
        merged = _deep_merge(merged, _load_simple_yaml(file_path))

    merged = _apply_env_overrides(merged)
    _validate(merged)
    return merged
