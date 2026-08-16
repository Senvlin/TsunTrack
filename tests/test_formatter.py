"""纯函数测试：异常消息格式化相关函数。
"""

from tsuntrack import formatter
from tsuntrack.formatter import (
    DEFAULT_TEMPLATE,
    _extract_name,
    _safe_str,
    build_context,
    format_message,
    resolve_exception_config,
)


def _raise_value_error() -> None:
    raise ValueError("boom")


def _get_value_error() -> tuple[type[ValueError], ValueError, object]:
    try:
        _raise_value_error()
    except ValueError as exc:
        return ValueError, exc, exc.__traceback__


class _BadStrError(Exception):
    def __str__(self) -> str:
        raise RuntimeError("bad __str__")


def test_safe_str_returns_empty_for_none():
    assert _safe_str(None) == ""


def test_safe_str_returns_normal_message():
    assert _safe_str(ValueError("hello")) == "hello"


def test_safe_str_tolerates_str_raising():
    assert _safe_str(_BadStrError("x")) == ""


def test_extract_name_uses_exception_name_attribute():
    exc = NameError("name 'foo' is not defined")
    exc.name = "foo"

    assert _extract_name(NameError, exc) == "foo"


def test_extract_name_falls_back_to_message_regex():
    assert _extract_name(NameError, NameError("name 'bar' is not defined")) == "bar"
    assert (
        _extract_name(
            AttributeError,
            AttributeError("'Dummy' object has no attribute 'baz'"),
        )
        == "baz"
    )


def test_extract_name_module_not_found():
    exc = ModuleNotFoundError("No module named 'PIL'")
    exc.name = "PIL"

    assert _extract_name(ModuleNotFoundError, exc) == "PIL"


def test_extract_name_key_error():
    assert _extract_name(KeyError, KeyError("missing_key")) == "missing_key"
    assert _extract_name(KeyError, KeyError(42)) == "42"


def test_extract_name_oserror_filename():
    exc = FileNotFoundError(2, "No such file or directory", "foo.txt")
    assert _extract_name(OSError, exc) == "foo.txt"


def test_extract_name_oserror_single_string_arg():
    exc = FileNotFoundError("only.txt")
    assert _extract_name(OSError, exc) == "only.txt"


def test_extract_name_returns_empty_for_unknown_message():
    assert _extract_name(ValueError, ValueError("just a value")) == ""


def test_extract_name_cannot_access_local_variable():
    exc = NameError(
        "cannot access local variable 'local_name' where it is not associated with a value"
    )
    assert _extract_name(NameError, exc) == "local_name"


def test_extract_name_local_variable_referenced_before_assignment():
    exc = NameError("local variable 'later_name' referenced before assignment")
    assert _extract_name(NameError, exc) == "later_name"


def test_extract_name_generic_is_not_defined():
    assert _extract_name(NameError, NameError("'some_name' is not defined")) == "some_name"



def test_build_context_with_traceback():
    exc_type, exc_value, tb = _get_value_error()

    ctx = build_context(exc_type, exc_value, tb)

    assert ctx["exc_type"] == "ValueError"
    assert ctx["message"] == "boom"
    assert ctx["name"] == ""
    assert ctx["filename"].endswith("test_formatter.py")
    assert ctx["lineno"] > 0
    assert ctx["func_name"] == "_raise_value_error"
    assert ctx["module"] == "test_formatter"
    assert ctx["exc_filename"] == ""


def test_build_context_without_traceback():
    ctx = build_context(ValueError, ValueError("boom"), None)

    assert ctx["exc_type"] == "ValueError"
    assert ctx["message"] == "boom"
    assert ctx["filename"] == ""
    assert ctx["lineno"] == 0
    assert ctx["func_name"] == ""
    assert ctx["module"] == ""


def test_build_context_fills_oserror_exc_filename():
    exc = FileNotFoundError(2, "No such file or directory", "foo.txt")

    ctx = build_context(OSError, exc, None)

    assert ctx["exc_filename"] == "foo.txt"


def test_build_context_falls_back_to_filename2():
    exc = OSError("some error")
    exc.filename2 = "second.txt"

    ctx = build_context(OSError, exc, None)

    assert ctx["exc_filename"] == "second.txt"



def test_resolve_exception_config_uses_specific_then_default():
    cfg = {
        "exceptions": {
            "ValueError": {"template": "V"},
            "default": {"template": "D"},
        }
    }

    assert resolve_exception_config(cfg, "ValueError") == {"template": "V"}
    assert resolve_exception_config(cfg, "NameError") == {"template": "D"}


def test_resolve_exception_config_returns_empty_for_missing():
    assert resolve_exception_config({}, "ValueError") == {}
    assert resolve_exception_config({"exceptions": {}}, "ValueError") == {}


def test_format_message_uses_custom_template():
    exc_type, exc_value, tb = _get_value_error()
    cfg = {"exceptions": {"ValueError": {"template": "自定义: {message}"}}}

    assert format_message(exc_type, exc_value, tb, cfg) == "自定义: boom"


def test_format_message_uses_default_template_when_missing():
    exc_type, exc_value, tb = _get_value_error()

    assert format_message(exc_type, exc_value, tb, {}) == DEFAULT_TEMPLATE.format(
        exc_type="ValueError", message="boom"
    )


def test_format_message_preserves_unknown_placeholders():
    exc_type, exc_value, tb = _get_value_error()
    cfg = {"exceptions": {"ValueError": {"template": "{message} {unknown}"}}}

    assert format_message(exc_type, exc_value, tb, cfg) == "boom {unknown}"


def test_format_message_merges_extra_placeholders():
    exc_type, exc_value, tb = _get_value_error()
    cfg = {"exceptions": {"ValueError": {"template": "{service}: {message}"}}}

    assert (
        format_message(exc_type, exc_value, tb, cfg, extra={"service": "api"})
        == "api: boom"
    )


def test_format_message_extra_overrides_builtin_context():
    exc_type, exc_value, tb = _get_value_error()
    cfg = {"exceptions": {"ValueError": {"template": "{message}"}}}

    assert format_message(
        exc_type, exc_value, tb, cfg, extra={"message": "custom"}
    ) == "custom"



def test_format_message_loads_config_when_cfg_none(monkeypatch):
    exc_type, exc_value, tb = _get_value_error()
    monkeypatch.setattr(
        formatter._config,
        "load_config",
        lambda use_cache=True: {
            "exceptions": {"ValueError": {"template": "自动加载: {message}"}}
        },
    )

    assert format_message(exc_type, exc_value, tb) == "自动加载: boom"
