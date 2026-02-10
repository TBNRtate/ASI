from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asi.safety.redact import redact_dict


class EventLogger:
    def __init__(self, config: dict[str, Any]) -> None:
        obs = config.get("observability", {})
        self.enabled = bool(obs.get("enabled", False))
        self.log_dir = Path(str(obs.get("log_dir", "./data/logs")))
        self.rotate_daily = bool(obs.get("rotate_daily", True))
        self.include_payloads = bool(obs.get("include_payloads", True))
        self.redact_secrets = bool(obs.get("redact_secrets", True))
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _path(self) -> Path:
        if self.rotate_daily:
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return self.log_dir / f"events-{day}.jsonl"
        return self.log_dir / "events.jsonl"

    def log(self, event_type: str, run_id: str, session_id: str, data: dict[str, Any]) -> None:
        if not self.enabled:
            return
        payload = dict(data)
        if self.redact_secrets:
            payload = redact_dict(payload)
        record = {
            "ts": time.time(),
            "event_type": event_type,
            "run_id": run_id,
            "session_id": session_id,
            "data": payload,
        }
        with self._path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
