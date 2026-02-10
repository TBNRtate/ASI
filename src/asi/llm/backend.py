from __future__ import annotations

from typing import Iterator, Protocol, TypedDict


class Message(TypedDict):
    role: str
    content: str


class LLMBackend(Protocol):
    def generate(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> str: ...

    def stream_generate(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        **kwargs: object,
    ) -> Iterator[str]: ...

    def tokenize(self, text: str) -> list[int]: ...

    def count_tokens(self, text: str) -> int:
        return len(self.tokenize(text))
