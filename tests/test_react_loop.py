from asi.brain.react_loop import ReActLoop
from asi.llm.null_backend import NullBackend
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
    assert any(
        "[tool_result]" in msg["content"] for msg in loop.debug_trace if msg["role"] == "user"
    )
