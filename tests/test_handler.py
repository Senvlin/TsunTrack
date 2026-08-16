"""handler 测试：纯函数 + 全局钩子安装/卸载。
"""

import sys

import tsuntrack.handler as handler
from tsuntrack import config as _config
from tsuntrack import renderer as renderer_module



def test_install_sets_hook_and_uninstall_restores(monkeypatch):
    old_hook = sys.excepthook
    monkeypatch.setattr(handler, "_installed", False)
    monkeypatch.setattr(handler, "_original_excepthook", None)
    monkeypatch.setattr(
        _config,
        "load_config",
        lambda use_cache=True: {"general": {"enabled": True}},
    )

    try:
        assert handler.install() is True
        assert sys.excepthook is handler.tsuntrack_excepthook
        # install 是幂等的
        assert handler.install() is True
    finally:
        handler.uninstall()

    assert sys.excepthook is old_hook


def test_install_disabled_does_not_replace_hook(monkeypatch):
    old_hook = sys.excepthook
    monkeypatch.setattr(handler, "_installed", False)
    monkeypatch.setattr(handler, "_original_excepthook", None)
    monkeypatch.setattr(
        _config,
        "load_config",
        lambda use_cache=True: {"general": {"enabled": False}},
    )

    try:
        assert handler.install() is False
        assert sys.excepthook is old_hook
    finally:
        handler.uninstall()


def test_tsuntrack_excepthook_passes_through_special_exceptions(monkeypatch):
    calls = []
    monkeypatch.setattr(
        handler,
        "_original_excepthook",
        lambda *args: calls.append(args),
    )

    handler.tsuntrack_excepthook(SystemExit, SystemExit(0), None)
    handler.tsuntrack_excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
    handler.tsuntrack_excepthook(GeneratorExit, GeneratorExit(), None)

    assert len(calls) == 3



def test_tsuntrack_excepthook_renders_normal_exception(monkeypatch):
    render_calls = []
    monkeypatch.setattr(
        _config,
        "load_config",
        lambda use_cache=True: {
            "general": {"enabled": True, "show_hints": True, "max_frames": 5},
            "exceptions": {"ValueError": {"template": "自定义: {message}"}},
            "hints": {},
        },
    )
    monkeypatch.setattr(
        renderer_module,
        "render",
        lambda *args, **kwargs: render_calls.append((args, kwargs)),
    )

    try:
        raise ValueError("boom")
    except ValueError as exc:
        handler.tsuntrack_excepthook(ValueError, exc, exc.__traceback__)

    assert len(render_calls) == 1
    args, _ = render_calls[0]
    assert args[4] == "自定义: boom"



def test_tsuntrack_excepthook_falls_back_when_render_fails(monkeypatch):
    fallback_calls = []
    monkeypatch.setattr(
        _config,
        "load_config",
        lambda use_cache=True: {
            "general": {"enabled": True, "show_hints": True, "max_frames": 5},
            "exceptions": {"ValueError": {"template": "x"}},
            "hints": {},
        },
    )
    monkeypatch.setattr(
        renderer_module,
        "render",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("render boom")),
    )
    monkeypatch.setattr(
        sys,
        "__excepthook__",
        lambda *args: fallback_calls.append(args),
    )

    try:
        raise ValueError("boom")
    except ValueError as exc:
        handler.tsuntrack_excepthook(ValueError, exc, exc.__traceback__)

    assert len(fallback_calls) == 1


def test_tsuntrack_excepthook_swallows_fallback_errors(monkeypatch):
    monkeypatch.setattr(
        _config,
        "load_config",
        lambda use_cache=True: {
            "general": {"enabled": True, "show_hints": True, "max_frames": 5},
            "exceptions": {"ValueError": {"template": "x"}},
            "hints": {},
        },
    )
    monkeypatch.setattr(
        renderer_module,
        "render",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("render boom")),
    )
    monkeypatch.setattr(
        sys,
        "__excepthook__",
        lambda *args: (_ for _ in ()).throw(RuntimeError("fallback boom")),
    )

    try:
        raise ValueError("boom")
    except ValueError as exc:
        # 不应向外抛异常
        handler.tsuntrack_excepthook(ValueError, exc, exc.__traceback__)
