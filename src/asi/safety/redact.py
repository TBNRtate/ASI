from __future__ import annotations

from typing import Any, cast

_REDACT_KEYS = {"api_key", "token", "authorization", "password", "secret"}


def redact_dict(d: dict[str, Any]) -> dict[str, Any]:
    def _redact(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: ("***REDACTED***" if k.lower() in _REDACT_KEYS else _redact(v))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [_redact(v) for v in value]
        return value

    return cast(dict[str, Any], _redact(d))
