"""装配器: 按配置安装/卸载各项异常出口钩子; 提供公共渲染编排 tsuntrack_excepthook。

SOLID 说明:
- SRP: handler 只做"装配 + 公共渲染编排 + 并发输出锁定"; 每个异常出口的注册/恢复都在
  hooks.py 各自的 Hook 类里(每个 Hook 一个职责)
- OCP: 新增异常出口(如 multiprocessing)只需实现一个 BaseHook 子类并加入 install 的装配列表,
  不改现有逻辑
- DIP: install/uninstall 依赖抽象接口 BaseHook(而非具体 Sys/Threading/Asyncio 类)
- ISP: BaseHook 接口最小(install/uninstall + name), 每个 Hook 只依赖自己出口需要的信息
"""

from __future__ import annotations

import sys
import threading

from . import config as _config
from . import formatter, hints
from . import hooks as _hooks

# 这些异常原样交给原始钩子处理, 不做美化
_PASSTHROUGH_TYPES: tuple[type[BaseException], ...] = (
    SystemExit,
    KeyboardInterrupt,
    GeneratorExit,
)

_installed = False
_installed_hooks: list[_hooks.BaseHook] = []
# 防止多线程同时报错时输出交错
_print_lock = threading.RLock()


def install() -> bool:
    """安装全局异常钩子(sys + threading + asyncio). 返回钩子是否处于启用状态"""
    global _installed, _installed_hooks
    if _installed:
        return True
    cfg = _config.load_config()
    if not cfg.get("general", {}).get("enabled", True):
        return False

    hook_list: list[_hooks.BaseHook] = [
        _hooks.SysHook(tsuntrack_excepthook),
        _hooks.ThreadingHook(tsuntrack_excepthook),
    ]
    if cfg.get("general", {}).get("asyncio_helper", True):
        hook_list.append(_hooks.AsyncioHook(tsuntrack_excepthook))

    for hook in hook_list:
        hook.install()
    _installed_hooks = hook_list
    _installed = True
    return True


def uninstall() -> None:
    """卸载钩子, 逆序恢复各出口的原始状态"""
    global _installed, _installed_hooks
    for hook in reversed(_installed_hooks):
        hook.uninstall()
    _installed_hooks = []
    _installed = False


def tsuntrack_excepthook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb,
    thread_name: str | None = None,
) -> None:
    with _print_lock:
        if issubclass(exc_type, _PASSTHROUGH_TYPES):
            return sys.__excepthook__(exc_type, exc_value, exc_tb)

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
            render(
                console,
                exc_type,
                exc_value,
                exc_tb,
                message,
                config,
                hint,
                thread_name=thread_name,
            )
        except Exception:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
