from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]
    permission_level: str

    @abstractmethod
    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def validate_args(self, args: dict[str, Any]) -> tuple[bool, str]:
        _ = args
        return True, "ok"
