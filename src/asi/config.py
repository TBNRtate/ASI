from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _parse_scalar(raw: str) -> Any:
    value = raw.strip().strip('"').strip("'")
    if value == "[]":
        return []
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    return value


def _load_simple_yaml(path: Path) -> dict[str, Any]:
    """
    Minimal YAML loader for our config files.
    Supports:
      - nested mappings via indentation
      - lists with '- '
      - multi-line blocks with '|'
    Intentionally not a full YAML implementation.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
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

        # List item
        if stripped.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Invalid YAML list context in {path}: {raw_line}")
            parent.append(_parse_scalar(stripped[2:]))
            continue

        # Key: value
        key, sep, remainder = stripped.partition(":")
        if not sep:
            raise ValueError(f"Invalid YAML line in {path}: {raw_line}")
        key = key.strip()
        value_text = remainder.strip()

        # Block scalar
        if value_text == "|":
            if not isinstance(parent, dict):
                raise ValueError(f"Invalid YAML mapping context in {path}: {raw_line}")

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
                # strip the indentation level plus two spaces (common YAML style)
                block_lines.append(next_line[indent + 2 :])
                i += 1

            parent[key] = "\n".join(block_lines).strip()
            continue

        if not isinstance(parent, dict):
            raise ValueError(f"Invalid YAML structure in {path}: {raw_line}")

        # Nested structure
        if value_text == "":
            # Decide dict vs list based on lookahead
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
        # preferred:
        "ASI_MEMORY_K_DEFAULT": ("memory", "k_default"),
        # legacy compatibility:
        "ASI_MEMORY_K": ("memory", "k"),
        "ASI_MEMORY_BACKEND": ("memory", "backend"),
        "ASI_SAFETY_PERMISSION_MODE": ("safety", "permission_mode"),
    }

    updated: dict[str, Any] = dict(config)
    for env_key, path in env_map.items():
        if env_key not in os.environ:
            continue
        cursor: Any = updated
        for part in path[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[path[-1]] = _parse_scalar(os.environ[env_key])

    return updated


def _compat_shims(config: dict[str, Any]) -> dict[str, Any]:
    """
    Small compatibility layer so older configs/tests don't explode:
      - prefer memory.k_default, but accept memory.k
      - accept prompts.system as system_base if system_base missing
    """
    updated = dict(config)

    mem = dict(updated.get("memory", {}))
    if "k_default" not in mem and "k" in mem:
        mem["k_default"] = mem["k"]
    if "k" not in mem and "k_default" in mem:
        mem["k"] = mem["k_default"]
    updated["memory"] = mem

    prompts = dict(updated.get("prompts", {}))
    if "system_base" not in prompts and "system" in prompts:
        prompts["system_base"] = prompts["system"]
    if "tool_instructions" not in prompts:
        # provide a sane default if missing
        prompts["tool_instructions"] = "Always respond with valid JSON."
    updated["prompts"] = prompts

    return updated


def _validate(config: dict[str, Any]) -> None:
    required = [
        ("models", "backend"),
        ("platform", "acceleration"),
        ("agent", "max_steps"),
        ("memory", "backend"),
        ("memory", "k_default"),
        ("safety", "permission_mode"),
        ("tools", "enabled_tools"),
        ("prompts", "system_base"),
        ("prompts", "tool_instructions"),
    ]

    missing: list[str] = []
    for path in required:
        cursor: Any = config
        ok = True
        for part in path:
            if not isinstance(cursor, dict) or part not in cursor:
                ok = False
                break
            cursor = cursor[part]
        if not ok:
            missing.append(".".join(path))

    memory_backend = str(config.get("memory", {}).get("backend", ""))
    if memory_backend == "sqlite":
        for key in ("db_path", "embedding_dim"):
            if key not in config.get("memory", {}):
                missing.append(f"memory.{key}")

    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(sorted(set(missing)))}")

    if config["models"]["backend"] not in {"llama_cpp", "null_backend", "null"}:
        raise ValueError("models.backend must be one of: llama_cpp, null_backend, null")
    if config["platform"]["acceleration"] not in {"cpu", "metal"}:
        raise ValueError("platform.acceleration must be one of: cpu, metal")
    if config["safety"]["permission_mode"] not in {"deny", "auto", "ask"}:
        raise ValueError("safety.permission_mode must be one of: deny, auto, ask")
    if memory_backend not in {"memory", "sqlite"}:
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
    merged = _compat_shims(merged)
    _validate(merged)
    return merged
