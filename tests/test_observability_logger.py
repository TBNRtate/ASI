import json
from pathlib import Path

from asi.observability.logger import EventLogger


def test_event_logger_writes_jsonl_with_required_fields(tmp_path: Path) -> None:
    cfg = {
        "observability": {
            "enabled": True,
            "log_dir": str(tmp_path),
            "rotate_daily": False,
            "include_payloads": True,
            "redact_secrets": True,
        }
    }
    logger = EventLogger(cfg)

    logger.log("event_a", run_id="r1", session_id="s1", data={"x": 1})
    logger.log("event_b", run_id="r2", session_id="s2", data={"token": "secret-token"})

    log_file = tmp_path / "events.jsonl"
    assert log_file.exists()

    lines = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert len(lines) == 2
    for row in lines:
        assert "ts" in row
        assert "event_type" in row
        assert "run_id" in row
        assert "session_id" in row
        assert "data" in row
    assert lines[1]["data"]["token"] == "***REDACTED***"
