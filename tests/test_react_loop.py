import json
from pathlib import Path

from asi.brain.react_loop import ReActLoop
from asi.llm.null_backend import NullBackend
from asi.observability.logger import EventLogger
from asi.safety.permissions import PermissionManager
from asi.tools.echo_tool import EchoTool
from asi.tools.registry import ToolRegistry


def _tools(permission_mode: str = "ask") -> ToolRegistry:
    reg = ToolRegistry(
        permission_manager=PermissionManager({"safety": {"permission_mode": permission_mode}})
    )
    reg.register(EchoTool())
    return reg


def test_react_loop_final_path_returns_final_content() -> None:
    loop = ReActLoop()
    out = loop.run(
        user_message="hello",
        system_prompt="system",
        tools=_tools(),
        llm=NullBackend(),
        max_steps=4,
        run_id="r1",
        session_id="s1",
    )
    assert out == "NullBackend: hello"


def test_react_loop_tool_path_executes_and_injects_result() -> None:
    loop = ReActLoop()
    out = loop.run(
        user_message="please use_tool now",
        system_prompt="system",
        tools=_tools(),
        llm=NullBackend(),
        max_steps=4,
        run_id="r1",
        session_id="s1",
    )
    assert out == "Tool returned: hi"
    assert any("[tool_result]" in m["content"] for m in loop.debug_trace if m["role"] == "user")


def test_react_loop_batch_tool_calls() -> None:
    loop = ReActLoop()
    out = loop.run(
        user_message="please batch",
        system_prompt="system",
        tools=_tools(),
        llm=NullBackend(),
        max_steps=4,
        run_id="r1",
        session_id="s1",
    )
    assert out == "Tool returned: second"


def test_react_loop_repair_once_and_logs_protocol_error(tmp_path: Path) -> None:
    loop = ReActLoop()
    logger = EventLogger(
        {
            "observability": {
                "enabled": True,
                "log_dir": str(tmp_path),
                "rotate_daily": False,
                "include_payloads": True,
                "redact_secrets": True,
            }
        }
    )
    out = loop.run(
        user_message="please break_json",
        system_prompt="system",
        tools=_tools(),
        llm=NullBackend(),
        max_steps=4,
        run_id="r1",
        session_id="s1",
        logger=logger,
    )
    assert out == "Recovered after protocol repair."

    lines = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert any(line["event_type"] == "protocol_error" for line in lines)
