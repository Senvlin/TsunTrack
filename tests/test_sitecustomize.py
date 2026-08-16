"""sitecustomize 自动安装失败时的兜底测试。"""

import importlib
import sys

import tsuntrack


def test_auto_install_handles_install_failure(monkeypatch, capsys):
    def boom():
        raise RuntimeError("install boom")

    monkeypatch.setattr(tsuntrack, "install", boom)

    # 确保 sitecustomize 在本次测试进程中重新导入，触发模块级 _auto_install()。
    sys.modules.pop("tsuntrack.sitecustomize", None)
    importlib.import_module("tsuntrack.sitecustomize")

    err = capsys.readouterr().err
    assert "自动安装失败" in err
    assert "install boom" in err
