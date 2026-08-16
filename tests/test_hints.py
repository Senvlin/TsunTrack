"""纯函数测试：智能提示相关的无副作用函数。
"""

from tsuntrack import config as _config
from tsuntrack.hints import _did_you_mean, _pip_name, build_hint


def _raise_name_error() -> None:
    value = 42
    return val  # noqa: F821


def _get_name_error() -> tuple[type[NameError], NameError, object]:
    try:
        _raise_name_error()
    except NameError as exc:
        return NameError, exc, exc.__traceback__


class _Dummy:
    def __init__(self) -> None:
        self.value = 1


def test_pip_name_returns_empty_for_empty_name():
    assert _pip_name("", {}) == ""


def test_pip_name_uses_alias_table():
    cfg = {"hints": {"aliases": {"PIL": "pillow", "cv2": "opencv-python"}}}

    assert _pip_name("PIL", cfg) == "pillow"
    assert _pip_name("cv2", cfg) == "opencv-python"


def test_pip_name_returns_original_name_without_alias():
    assert _pip_name("numpy", {"hints": {"aliases": {}}}) == "numpy"


def test_pip_name_returns_name_when_hints_config_missing():
    assert _pip_name("numpy", {}) == "numpy"



def test_did_you_mean_suggests_name_error_from_locals():
    exc_type, exc_value, _ = _get_name_error()

    assert _did_you_mean(exc_type, exc_value) == "value"


def test_did_you_mean_suggests_attribute_error_from_obj():
    obj = _Dummy()
    exc = AttributeError("'Dummy' object has no attribute 'val'")
    exc.name = "val"
    exc.obj = obj

    assert _did_you_mean(AttributeError, exc) == "value"


def test_did_you_mean_returns_empty_when_no_suggestion():
    exc = NameError("name 'xyzabc' is not defined")
    exc.name = "xyzabc"

    assert _did_you_mean(NameError, exc) == ""


def test_did_you_mean_returns_empty_for_attribute_error_without_obj():
    exc = AttributeError("'Dummy' object has no attribute 'val'")
    exc.name = "val"

    assert _did_you_mean(AttributeError, exc) == ""


def test_did_you_mean_returns_empty_when_name_missing():
    exc = NameError("name 'x' is not defined")

    assert _did_you_mean(NameError, exc) == ""




def test_build_hint_returns_none_when_disabled():
    cfg = {"general": {"show_hints": False}, "hints": {"ValueError": {"template": "x"}}}

    assert build_hint(ValueError, ValueError("x"), None, cfg) is None


def test_build_hint_returns_none_without_matching_config():
    assert build_hint(ValueError, ValueError("x"), None, {}) is None


def test_build_hint_uses_pip_name_alias():
    cfg = {
        "general": {"show_hints": True},
        "hints": {
            "ModuleNotFoundError": {"template": "pip install {pip_name}"},
            "aliases": {"PIL": "pillow"},
        },
    }
    exc = ModuleNotFoundError("No module named 'PIL'")
    exc.name = "PIL"

    assert build_hint(ModuleNotFoundError, exc, None, cfg) == "pip install pillow"


def test_build_hint_uses_did_you_mean():
    cfg = {
        "general": {"show_hints": True},
        "hints": {"NameError": {"template": "你是不是想写 {did_you_mean}?"}},
    }
    exc_type, exc_value, tb = _get_name_error()

    assert build_hint(exc_type, exc_value, tb, cfg) == "你是不是想写 value?"


def test_build_hint_returns_none_when_no_did_you_mean():
    cfg = {
        "general": {"show_hints": True},
        "hints": {"NameError": {"template": "你是不是想写 {did_you_mean}?"}},
    }
    exc = NameError("name 'xyzabc' is not defined")
    exc.name = "xyzabc"

    assert build_hint(NameError, exc, None, cfg) is None


def test_build_hint_preserves_unknown_placeholders():
    cfg = {
        "general": {"show_hints": True},
        "hints": {"ValueError": {"template": "{message} {unknown}"}},
    }

    assert build_hint(ValueError, ValueError("x"), None, cfg) == "x {unknown}"



def test_build_hint_loads_config_when_cfg_none(monkeypatch):
    monkeypatch.setattr(
        _config,
        "load_config",
        lambda use_cache=True: {
            "general": {"show_hints": True},
            "hints": {"ValueError": {"template": "自动加载: {message}"}},
        },
    )

    assert build_hint(ValueError, ValueError("x"), None) == "自动加载: x"
