from __future__ import annotations

from typing import Any


class PersonaManager:
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    def get_persona_context(self, session_id: str) -> dict[str, Any]:
        _ = session_id
        prompts = self._config.get("prompts", {})
        style_prompt = str(prompts.get("persona_default", "Respond clearly and concisely."))
        return {
            "style_prompt": style_prompt,
            "adapter": None,
            "persona_name": "default",
        }
