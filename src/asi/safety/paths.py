from __future__ import annotations

from pathlib import Path


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def resolve_safe_path(base: Path, user_path: str) -> Path:
    base_resolved = base.resolve()
    candidate = (base_resolved / user_path).resolve()
    if not _is_relative_to(candidate, base_resolved):
        raise ValueError("path escapes allowed base")
    return candidate


def is_path_allowed(path: Path, allowed_roots: list[Path]) -> bool:
    resolved = path.resolve()
    return any(_is_relative_to(resolved, root.resolve()) for root in allowed_roots)
