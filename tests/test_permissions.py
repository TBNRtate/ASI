from asi.safety.permissions import (
    PermissionLevel,
    PermissionManager,
)


class _TestPrompter:
    def __init__(self, allow: bool) -> None:
        self.allow = allow

    def confirm(self, level: PermissionLevel, action_label: str | None = None) -> bool:
        _ = (level, action_label)
        return self.allow


def test_deny_mode_blocks_write_and_system() -> None:
    mgr = PermissionManager({"safety": {"permission_mode": "deny"}})
    assert mgr.is_allowed(PermissionLevel.READ)
    assert not mgr.is_allowed(PermissionLevel.WRITE)
    assert not mgr.is_allowed(PermissionLevel.SYSTEM)


def test_auto_mode_allows_read_write_and_blocks_system() -> None:
    mgr = PermissionManager({"safety": {"permission_mode": "auto"}})
    assert mgr.is_allowed(PermissionLevel.READ)
    assert mgr.is_allowed(PermissionLevel.WRITE)
    assert not mgr.is_allowed(PermissionLevel.SYSTEM)


def test_ask_mode_with_prompter() -> None:
    deny_mgr = PermissionManager(
        {"safety": {"permission_mode": "ask"}},
        prompter=_TestPrompter(allow=False),
    )
    allow_mgr = PermissionManager(
        {"safety": {"permission_mode": "ask"}},
        prompter=_TestPrompter(allow=True),
    )
    assert not deny_mgr.is_allowed(PermissionLevel.SYSTEM, action_label="shell")
    assert allow_mgr.is_allowed(PermissionLevel.SYSTEM, action_label="shell")
