"""自定义报错渲染

样式全部由配置文件驱动(见 defaults.toml / tsuntrack.toml 的 [general]):
- context_lines        报错行上下各显示几行
- error_line_style     报错行代码样式(如 bold hot_pink / orange1)
- line_number_style    行号样式(如 dim / grey)
- [general.syntax]     上下文代码高亮:
    theme              pygments 内置主题名(monokai/default/emacs/...), 留空用 styles 表
    styles             pygments token 名 → rich 样式(如 "Name.Function" = "#61AFEF")
"""

from __future__ import annotations

import linecache
import traceback
from dataclasses import dataclass
from typing import Any

from pygments import lex
from pygments.lexers.python import PythonLexer
from pygments.styles import get_style_by_name
from pygments.token import Token
from rich.console import Console
from rich.text import Text

_python_lexer = PythonLexer()


@dataclass(frozen=True)
class RenderConfig:
    context_lines: int = 1
    error_line_style: str = "orange1"
    line_number_style: str = "dim"
    syntax_theme: str = ""
    syntax_styles: dict[str, str] | None = None
    max_frames: int = 5
    hint_label: str = "Hint"
    hint_style: str = "bold orange1"

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "RenderConfig":
        """从合并后的配置(含 defaults + 主题 + 用户)构建渲染参数."""
        general = cfg.get("general") or {}
        syntax = general.get("syntax") or {}

        def _int(key: str, default: int) -> int:
            try:
                return int(general.get(key, default))
            except (TypeError, ValueError):
                return default

        return cls(
            context_lines=_int("context_lines", cls.context_lines),
            error_line_style=general.get("error_line_style") or cls.error_line_style,
            line_number_style=general.get("line_number_style") or cls.line_number_style,
            syntax_theme=syntax.get("theme", "") or "",
            syntax_styles=syntax.get("styles") or {},
            max_frames=_int("max_frames", cls.max_frames),
            hint_label=general.get("hint_label") or cls.hint_label,
            hint_style=general.get("hint_style") or cls.hint_style,
        )


def _resolve_token(name: str) -> object:
    """把 "Name.Function" 这样的字符串解析成 pygments token 对象."""
    current = Token
    for part in name.split("."):
        current = getattr(current, part)
    return current


def _is_subtype(token, token_type) -> bool:
    """判断 token 是否是 token_type 的子类型."""
    current = token
    while current is not None:
        if current is token_type:
            return True
        current = getattr(current, "parent", None)
    return False


def _build_token_style(theme: str, styles: dict[str, str] | None):
    """根据配置构建"token → rich 样式"的函数.

    - theme 非空: 使用 pygments 内置主题(只取前景色/粗体/斜体, 忽略背景色)
    - 否则: 使用 styles 自定义表
    """
    if theme:
        try:
            pyg_style = get_style_by_name(theme)
        except Exception:
            pyg_style = None
        if pyg_style is not None:

            def token_style(token) -> str:
                info = pyg_style.style_for_token(token)
                parts = []
                if info.get("bold"):
                    parts.append("bold")
                if info.get("italic"):
                    parts.append("italic")
                color = info.get("color")
                if color:
                    parts.append(f"#{color}")
                return " ".join(parts)

            return token_style

    table: list[tuple[object, str]] = []
    source = styles or {}
    for name, style in source.items():
        try:
            token = _resolve_token(name)
        except AttributeError:
            continue
        table.append((token, style))

    def token_style(token) -> str:
        for token_type, style in table:
            if _is_subtype(token, token_type):
                return style
        return ""

    return token_style


def _highlight_python_line(code: str, token_style) -> Text:
    """把一行 Python 代码按配置的配色方案着色, 返回带样式的 Text."""
    result = Text()
    for token, value in lex(code, _python_lexer):
        if "\n" in value:
            # pygments 会给单行输入补一个换行 token, 每个上下文行后面都会多出一个空行
            value = value.replace("\n", "")
            if not value:
                continue
        result.append(value, style=token_style(token))
    return result


def _render_source_block(
    console: Console,
    fs: traceback.FrameSummary,
    config: RenderConfig,
    token_style,
) -> None:
    """渲染报错行及其上下 config.context_lines 行, 报错行高亮, 每行带行号."""
    lineno = fs.lineno or 0
    if lineno <= 0:
        return

    lines = linecache.getlines(fs.filename)
    if not lines:
        return

    start = max(1, lineno - config.context_lines)
    end = min(len(lines), lineno + config.context_lines)
    for n in range(start, end + 1):
        code = lines[n - 1].rstrip("\n").rstrip()
        line_text = Text()
        line_text.append(f"{n:>4} │ ", style=config.line_number_style)
        if n == lineno:
            line_text.append(code, style=config.error_line_style)
        else:
            line_text.append_text(_highlight_python_line(code, token_style))
        console.print(line_text)


def render(
    console: Console,
    exc_type,
    exc_value,
    tb,
    message: str,
    style: str,
    config: RenderConfig,
    hint: str | None = None,
):
    frames: list[traceback.FrameSummary] = list(traceback.extract_tb(tb))[
        -config.max_frames :
    ]
    token_style = _build_token_style(config.syntax_theme, config.syntax_styles)
    for fs in frames:
        console.print(
            f"[dim]{fs.filename}:[/dim][green]{fs.lineno or 0}[/green] in "
            f"[bold cyan]{fs.name}[/bold cyan]",
            highlight=False,
        )
        _render_source_block(console, fs, config, token_style)
    console.print(
        f"\n[bold red]{exc_type.__name__}[/bold red]: {Text(message, style=style)}"
    )
    if hint:
        # 提示行: "Hint: 提示内容"，markup 安全（用 Text 拼接，不解析模板里的 [ ]）
        hint_text = Text()
        hint_text.append(f"{config.hint_label}: ", style=config.hint_style)
        hint_text.append(hint)
        console.print(hint_text)
