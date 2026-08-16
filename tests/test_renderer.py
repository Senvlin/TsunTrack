"""渲染器测试：纯函数 + 基础输出渲染。"""

import traceback
from io import StringIO

import pytest
from pygments.token import Token
from rich.console import Console

from tsuntrack import renderer as renderer_module
from tsuntrack.renderer import (
    RenderConfig,
    _build_token_style,
    _highlight_python_line,
    _is_subtype,
    _render_source_block,
    _resolve_token,
    render,
)


def _get_traceback():
    try:
        raise ValueError("boom")
    except ValueError as exc:
        return exc.__traceback__


def test_render_config_from_config_parses_fields():
    cfg = {
        "general": {
            "context_lines": "3",
            "error_line_style": "bold red",
            "line_number_style": "dim",
            "max_frames": "10",
            "syntax": {
                "theme": "monokai",
                "styles": {"Keyword": "bold red"},
            },
        }
    }

    config = RenderConfig.from_config(cfg)

    assert config.context_lines == 3
    assert config.error_line_style == "bold red"
    assert config.line_number_style == "dim"
    assert config.syntax_theme == "monokai"
    assert config.syntax_styles == {"Keyword": "bold red"}
    assert config.max_frames == 10


def test_render_config_from_config_uses_defaults_for_missing():
    config = RenderConfig.from_config({})

    assert config.context_lines == RenderConfig.context_lines
    assert config.error_line_style == RenderConfig.error_line_style
    assert config.line_number_style == RenderConfig.line_number_style
    assert config.syntax_theme == RenderConfig.syntax_theme
    assert config.max_frames == RenderConfig.max_frames
    assert config.syntax_styles == {}


def test_render_config_from_config_tolerates_invalid_int():
    cfg = {"general": {"context_lines": "abc", "max_frames": None}}

    config = RenderConfig.from_config(cfg)

    assert config.context_lines == RenderConfig.context_lines
    assert config.max_frames == RenderConfig.max_frames


def test_resolve_token_parses_dotted_name():
    assert _resolve_token("Name.Function") == Token.Name.Function


def test_resolve_token_dynamically_creates_uppercase_unknown():
    # Pygments 的 Token.__getattr__ 会把大写开头的未知名称动态创建成新 token。
    # 因此这里不会抛 AttributeError；但这类 token 不会被 PythonLexer 产出，
    # 所以配置里写了也不会影响真实渲染（defaults.toml 中已注明）。
    token = _resolve_token("No.Such.Token")

    assert token == Token.No.Such.Token


def test_resolve_token_raises_for_lowercase_unknown():
    with pytest.raises(AttributeError):
        _resolve_token("no.Such.Token")


def test_resolve_token_raises_for_lowercase_segment_after_valid_prefix():
    with pytest.raises(AttributeError):
        _resolve_token("Name.foo")


def test_is_subtype_handles_hierarchy():
    assert _is_subtype(Token.Name.Function, Token.Name.Function)
    assert _is_subtype(Token.Name.Function, Token.Name)
    assert not _is_subtype(Token.Name, Token.Name.Function)


def test_build_token_style_uses_styles_table():
    token_style = _build_token_style("", {"Keyword": "bold red"})

    assert token_style(Token.Keyword) == "bold red"
    assert token_style(Token.Keyword.Constant) == "bold red"
    assert token_style(Token.Name) == ""


def test_build_token_style_ignores_dynamic_tokens_for_real_code_tokens():
    token_style = _build_token_style("", {"No.Such.Token": "red"})

    # 动态创建出的 token 不会匹配 Name / Keyword 等真实 token，
    # 因此即使配置里写错也不会把正常代码染成错误颜色。
    assert token_style(Token.Name) == ""
    assert token_style(Token.Keyword) == ""


def test_build_token_style_mixed_dynamic_and_valid_styles():
    token_style = _build_token_style(
        "",
        {
            "No.Such.Token": "red",
            "Keyword": "bold blue",
        },
    )

    # 无效的动态 token 不影响同表里其他有效样式。
    assert token_style(Token.Keyword) == "bold blue"
    assert token_style(Token.Name) == ""


def test_build_token_style_skips_lowercase_invalid_style_names():
    token_style = _build_token_style("", {"keyword": "red"})

    assert token_style(Token.Keyword) == ""
    assert token_style(Token.Name) == ""


def test_build_token_style_accepts_theme():
    token_style = _build_token_style("monokai", {})

    assert callable(token_style)
    assert token_style(Token.Keyword) != ""


def test_build_token_style_falls_back_to_empty_for_unknown_theme():
    token_style = _build_token_style("definitely-not-a-theme", {})

    assert callable(token_style)
    assert token_style(Token.Keyword) == ""


def test_build_token_style_theme_applies_bold_italic_and_color(monkeypatch):
    class _FakeStyle:
        def style_for_token(self, token):
            return {"bold": True, "italic": True, "color": "ff0000"}

    monkeypatch.setattr(
        renderer_module, "get_style_by_name", lambda name: _FakeStyle()
    )

    token_style = _build_token_style("fake-theme", {})

    assert token_style(Token.Keyword) == "bold italic #ff0000"


def test_highlight_python_line_returns_same_plain_text_without_newline():
    text = _highlight_python_line("x = 1", lambda token: "bold red")

    assert text.plain == "x = 1"
    assert "\n" not in text.plain


def test_render_source_block_returns_early_for_non_positive_lineno():
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    fs = traceback.FrameSummary("nonexistent.py", 0, "func")

    _render_source_block(console, fs, RenderConfig(), lambda token: "")

    assert output.getvalue() == ""


def test_render_source_block_returns_early_when_no_lines():
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    fs = traceback.FrameSummary("definitely-no-such-file.py", 1, "func")

    _render_source_block(console, fs, RenderConfig(), lambda token: "")

    assert output.getvalue() == ""


def test_render_prints_message_and_hint():
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=120)
    tb = _get_traceback()

    render(
        console,
        ValueError,
        ValueError("boom"),
        tb,
        "自定义消息",
        RenderConfig(),
        hint="提示内容",
    )

    text = output.getvalue()
    assert "自定义消息" in text
    assert "Hint: 提示内容" in text
    assert "test_renderer.py" in text


def test_render_outputs_ansi_styles_not_literal_markup():
    output = StringIO()
    console = Console(
        file=output,
        force_terminal=True,
        color_system="truecolor",
        width=120,
        record=True,
    )
    tb = _get_traceback()

    render(
        console,
        ValueError,
        ValueError("boom"),
        tb,
        "自定义消息",
        RenderConfig(),
        hint="提示内容",
    )

    text = output.getvalue()
    assert "\x1b[" in text
    assert "[bold red]" not in text
    assert "[/bold red]" not in text

    # ANSI 样式码会插在 “Hint” 这类带样式的文本中间，
    # 所以子串断言用去样式后的纯文本。
    plain = console.export_text(styles=False, clear=False)
    assert "自定义消息" in plain
    assert "Hint: 提示内容" in plain

    styled = console.export_text(styles=True, clear=False)
    assert "\x1b[" in styled


def test_highlight_python_line_applies_styles():
    text = _highlight_python_line("x = 1", lambda token: "bold red")

    assert text.plain == "x = 1"
    assert any(span.style == "bold red" for span in text.spans)
