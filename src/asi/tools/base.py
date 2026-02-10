# ruff: noqa: I001
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

try:
    from jsonschema import ValidationError, validate as _jsonschema_validate  # type: ignore[import-untyped]
except Exception:  # pragma: no cover
    ValidationError = ValueError

    def _jsonschema_validate(instance: dict[str, Any], schema: dict[str, Any]) -> None:
        if schema.get("type") == "object" and not isinstance(instance, dict):
            raise ValidationError("instance must be object")

        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise ValidationError(f"'{key}' is a required property")

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    raise ValidationError(f"additional property '{key}' is not allowed")

        for key, rules in properties.items():
            if key not in instance:
                continue
            expected = rules.get("type")
            value = instance[key]
            if expected == "string" and not isinstance(value, str):
                raise ValidationError(f"'{key}' must be string")
            if expected == "array":
                if not isinstance(value, list):
                    raise ValidationError(f"'{key}' must be array")
                item_rules = rules.get("items", {})
                if item_rules.get("type") == "string" and not all(
                    isinstance(v, str) for v in value
                ):
                    raise ValidationError(f"'{key}' array items must be string")


class Tool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]
    permission_level: str

    @abstractmethod
    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def validate_args(self, args: dict[str, Any]) -> tuple[bool, str]:
        try:
            _jsonschema_validate(instance=args, schema=self.parameters)
        except ValidationError as exc:
            return False, str(exc)
        return True, "ok"
