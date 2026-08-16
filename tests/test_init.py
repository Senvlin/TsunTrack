"""tsuntrack 包公开接口 install/uninstall 测试。"""

import sys

import tsuntrack
import tsuntrack.handler as handler
from tsuntrack import config as _config


def test_public_install_and_uninstall(monkeypatch):
    old_hook = sys.excepthook
    monkeypatch.setattr(handler, "_installed", False)
    monkeypatch.setattr(handler, "_original_excepthook", None)
    monkeypatch.setattr(
        _config,
        "load_config",
        lambda use_cache=True: {"general": {"enabled": True}},
    )

    try:
        assert tsuntrack.install() is True
        assert sys.excepthook is handler.tsuntrack_excepthook

        tsuntrack.uninstall()
        assert sys.excepthook is old_hook
    finally:
        tsuntrack.uninstall()


def test_public_install_disabled(monkeypatch):
    old_hook = sys.excepthook
    monkeypatch.setattr(handler, "_installed", False)
    monkeypatch.setattr(handler, "_original_excepthook", None)
    monkeypatch.setattr(
        _config,
        "load_config",
        lambda use_cache=True: {"general": {"enabled": False}},
    )

    try:
        assert tsuntrack.install() is False
        assert sys.excepthook is old_hook
    finally:
        tsuntrack.uninstall()


def test_import_survives_stderr_without_reconfigure(monkeypatch):
    """回归测试: sys.stderr 被替换成无 reconfigure 方法的对象(GUI/嵌入/IDLE
    场景)时, import tsuntrack 不应崩溃.

    reload 会重新执行模块级代码; 若顶层又被加上无条件 reconfigure,
    这里会抛 AttributeError 让测试失败.
    """
    import importlib

    class DummyStderr:
        def write(self, s):
            pass

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stderr", DummyStderr())

    importlib.reload(tsuntrack)
