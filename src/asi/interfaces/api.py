from __future__ import annotations

from importlib import metadata
from pathlib import Path
from typing import Any

from asi.brain.arabella_brain import ArabellaBrain
from asi.observability.ids import new_run_id

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
except Exception:  # pragma: no cover - optional dependency
    FastAPI = None
    BaseModel = object


if FastAPI is not None:
    app = FastAPI()
else:  # pragma: no cover - optional dependency
    app = None

brain = ArabellaBrain(config_dir=Path("configs"))


class ChatRequest(BaseModel):
    session_id: str
    message: str


def _health_payload() -> dict[str, str]:
    try:
        version = metadata.version("asi")
    except Exception:
        version = "0.0.0"
    return {"status": "ok", "service": "ASI", "version": version}


def _chat_payload(session_id: str, message: str) -> dict[str, str]:
    run_id = new_run_id()
    response = brain.respond(message, session_id, run_id=run_id)
    return {"session_id": session_id, "run_id": run_id, "response": response}


if app is not None:

    @app.get("/health")
    def health() -> dict[str, str]:
        return _health_payload()

    @app.post("/chat")
    def chat(body: ChatRequest) -> dict[str, str]:
        return _chat_payload(body.session_id, body.message)

else:  # pragma: no cover

    def health() -> dict[str, str]:
        raise RuntimeError("fastapi extra is not installed")

    def chat(body: Any) -> dict[str, str]:
        raise RuntimeError("fastapi extra is not installed")
