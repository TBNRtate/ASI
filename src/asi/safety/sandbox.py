from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


class Sandbox:
    def __init__(self, config: dict[str, Any]) -> None:
        safety_cfg = config.get("safety", {})
        sandbox_cfg = safety_cfg.get("sandbox", {})
        self.working_dir = Path(str(sandbox_cfg.get("working_dir", "./workspace")))
        self.timeout_seconds = int(sandbox_cfg.get("timeout_seconds", 20))
        self.allowed_commands = [str(x) for x in sandbox_cfg.get("allowed_commands", [])]
        self.blocked_tokens = [str(x) for x in sandbox_cfg.get("blocked_tokens", [])]
        self.dangerous_patterns = [str(x) for x in safety_cfg.get("dangerous_patterns", [])]

    def execute(self, command: list[str]) -> dict[str, Any]:
        if not command:
            return {"success": False, "blocked": True, "error": "empty command"}

        command_name = command[0]
        joined = " ".join(command)

        if any(re.search(pattern, joined) for pattern in self.dangerous_patterns):
            return {"success": False, "blocked": True, "error": "dangerous pattern blocked"}

        if command_name not in self.allowed_commands:
            return {"success": False, "blocked": True, "error": "command not in allowlist"}

        for token in command:
            if any(blocked in token or token == blocked for blocked in self.blocked_tokens):
                return {"success": False, "blocked": True, "error": "blocked token in command"}

        self.working_dir.mkdir(parents=True, exist_ok=True)
        try:
            completed = subprocess.run(
                command,
                shell=False,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            return {
                "success": True,
                "blocked": False,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "returncode": completed.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "blocked": True, "error": "command timed out"}
