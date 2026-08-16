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
