"""自定义 sys.excepthook: 输出傲娇报错文本 + rich 美化堆栈"""

from __future__ import annotations

import sys
import types
from typing import Any

from . import config as _config
from . import formatter, hints
from .renderer import RenderConfig, render

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


def _limit_traceback(tb, max_frames: int | None):
    """保留最内层(离异常最近)的 max_frames 帧, 返回新的回溯链头

    rich 15 的 max_frames 语义是"保留栈顶一半 + 栈底一半、
    隐藏中间", 且强制最少 4 帧; 而配置里 max_frames 的语义是"最多显示 N 层、
    保留最内层", 两者不一致
    """
    if max_frames is None or max_frames <= 0:
        return tb
    frames = []
    cur = tb
    while cur is not None:
        frames.append(cur)
        cur = cur.tb_next
    if len(frames) <= max_frames:
        return tb
    keep = frames[-max_frames:]
    new_tb = None
    for frame_tb in reversed(keep):
        new_tb = types.TracebackType(
            new_tb, frame_tb.tb_frame, frame_tb.tb_lasti, frame_tb.tb_lineno
        )
    return new_tb


def tsuntrack_excepthook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb,
) -> None:
    """自定义 excepthook: 打印傲娇消息 + rich 美化堆栈"""
    original = (
        _original_excepthook if _original_excepthook is not None else sys.__excepthook__
    )
    if issubclass(exc_type, _PASSTHROUGH_TYPES):
        return original(exc_type, exc_value, exc_tb)

    try:
        cfg = _config.load_config()
        message = formatter.format_message(exc_type, exc_value, exc_tb, cfg)

        config: RenderConfig = RenderConfig.from_config(cfg)

        # rich 延迟导入: 只有真正报错时才付出 import 成本
        from rich.console import Console

        console = Console(stderr=True)
        # 先按"保留最内层 N 帧"修剪回溯链(max_frames<=0 表示不限制)
        tb_for_render = _limit_traceback(exc_tb, config.max_frames)
        # 智能提示（pip install / did you mean 等），没有合适提示时为 None
        hint = hints.build_hint(exc_type, exc_value, exc_tb, cfg)
        render(console, exc_type, exc_value, tb_for_render, message, config, hint)
    except Exception:
        try:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        except Exception:
            pass
