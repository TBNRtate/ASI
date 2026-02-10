from __future__ import annotations

from asi.llm.backend import Message


class EmotionState:
    def update(self, user_message: str, history: list[Message]) -> None:
        _ = (user_message, history)

    def to_prompt_modifier(self) -> str:
        return ""
