"""自定义 sys.excepthook: 输出傲娇报错文本 + rich 美化堆栈"""

from __future__ import annotations

import sys
from typing import Any

from . import config as _config
from . import formatter, hints

# 这些异常原样交给原始钩子处理, 不做美化
_PASSTHROUGH_TYPES: tuple[type[BaseException], ...] = (
    SystemExit,
    KeyboardInterrupt,
    GeneratorExit,
)

_original_excepthook: Any = None
_installed = False


def install() -> bool:
    """安装全局异常钩子. 返回钩子是否处于启用状态"""
    global _original_excepthook, _installed
    if _installed:
        return True
    cfg = _config.load_config()
    if not cfg.get("general", {}).get("enabled", True):
        return False
    _original_excepthook = sys.excepthook
    sys.excepthook = tsuntrack_excepthook
    _installed = True
    return True


def uninstall() -> None:
    """卸载钩子, 恢复安装前的 excepthook"""
    global _original_excepthook, _installed
    if _installed and _original_excepthook is not None:
        sys.excepthook = _original_excepthook
    _installed = False
    _original_excepthook = None


def tsuntrack_excepthook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb,
) -> None:
    """自定义 excepthook: 打印傲娇消息 + rich 美化堆栈"""
    original = (
        _original_excepthook
        if _original_excepthook is not None
        else sys.__excepthook__
    )
    if issubclass(exc_type, _PASSTHROUGH_TYPES):
        return original(exc_type, exc_value, exc_tb)

    try:
        cfg = _config.load_config()
        # defaults.toml 不内置extra段, 使用者按需在自己的配置里添加
        message = formatter.format_message(
            exc_type,
            exc_value,
            exc_tb,
            cfg,
            extra=cfg.get("extra") or {},
        )
        from .renderer import RenderConfig, render

        config: RenderConfig = RenderConfig.from_config(cfg)

        # rich 延迟导入: 只有真正报错时才付出 import 成本
        if not sys.stderr.isatty():
            try:
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
            except (AttributeError, ValueError, OSError):
                pass
        from rich.console import Console

        console = Console(stderr=True)

        # 智能提示, 没有合适提示时为 None
        hint = hints.build_hint(exc_type, exc_value, exc_tb, cfg)
        render(console, exc_type, exc_value, exc_tb, message, config, hint)
    except Exception:
        try:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        except Exception:
            pass
