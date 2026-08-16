"""handler 测试：纯函数 + 全局钩子安装/卸载。
"""

import sys

import tsuntrack.handler as handler
from tsuntrack import config as _config
from tsuntrack.handler import _limit_traceback


def _level1() -> None:
    _level2()


def _level2() -> None:
    raise ValueError("boom")


def _get_traceback():
    try:
        _level1()
    except ValueError as exc:
        return exc.__traceback__


def _tb_frame_names(tb) -> list[str]:
    names = []
    current = tb
    while current is not None:
        names.append(current.tb_frame.f_code.co_name)
        current = current.tb_next
    return names


def test_limit_traceback_returns_same_for_none_or_non_positive():
    tb = _get_traceback()

    assert _limit_traceback(tb, None) is tb
    assert _limit_traceback(tb, 0) is tb
    assert _limit_traceback(tb, -1) is tb


def test_limit_traceback_returns_same_when_within_limit():
    tb = _get_traceback()

    assert _limit_traceback(tb, 100) is tb


def test_limit_traceback_keeps_innermost_frames():
    tb = _get_traceback()
    names = _tb_frame_names(tb)

    limited = _limit_traceback(tb, 1)

    assert _tb_frame_names(limited) == names[-1:]


def test_limit_traceback_keeps_multiple_innermost_frames():
    tb = _get_traceback()
    names = _tb_frame_names(tb)

    limited = _limit_traceback(tb, 2)

    assert _tb_frame_names(limited) == names[-2:]



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
        handler,
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
        handler,
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
        handler,
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
