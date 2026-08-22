"""各异常出口的钩子适配器"""

from __future__ import annotations

import asyncio
import sys
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

# 公共渲染入口的签名: (exc_type, exc_value, exc_tb, thread_name=None)
Sink = Callable[..., None]


class BaseHook(ABC):
    name: str = ""

    def __init__(self, sink: Sink) -> None:
        self._sink = sink

    @abstractmethod
    def install(self) -> None:
        """注册本出口的钩子并保存原始状态。"""

    @abstractmethod
    def uninstall(self) -> None:
        """恢复本出口的原始状态。"""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.name})>"


class SysHook(BaseHook):
    name = "sys.excepthook"
    _original: Any = None

    def install(self) -> None:
        self._original = sys.excepthook
        sys.excepthook = self._adapter

    def uninstall(self) -> None:
        if self._original is not None:
            sys.excepthook = self._original
            self._original = None

    def _adapter(self, exc_type, exc_value, exc_tb) -> None:
        self._sink(exc_type, exc_value, exc_tb)


class ThreadingHook(BaseHook):
    name = "threading.excepthook"
    _original: Any = None

    def install(self) -> None:
        self._original = threading.excepthook
        threading.excepthook = self._adapter

    def uninstall(self) -> None:
        if self._original is not None:
            threading.excepthook = self._original
            self._original = None

    def _adapter(self, args) -> None:
        # args: threading.ExceptHookArgs(exc_type, exc_value, exc_traceback, thread)
        thread_name = getattr(getattr(args, "thread", None), "name", None) or ""
        self._sink(
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
            thread_name=thread_name,
        )


class AsyncioHook(BaseHook):
    name = "asyncio.loop"
    _original_policy: Any = None
    _policy: Any = None

    def install(self) -> None:
        self._original_policy = asyncio.get_event_loop_policy()  # ty: ignore[deprecated]
        self._policy = _WrappedPolicy(self._original_policy, self._loop_handler)
        asyncio.set_event_loop_policy(self._policy)  # ty: ignore[deprecated]

    def uninstall(self) -> None:
        if self._original_policy is not None:
            asyncio.set_event_loop_policy(self._original_policy)  # ty: ignore[deprecated]
            self._original_policy = None
            self._policy = None

    def _loop_handler(self, loop, context) -> None:
        exception = context.get("exception")
        if exception is None:
            return  # 非异常消息(asyncio 内部日志/网络告警)不渲染, 保持低打扰
        self._sink(type(exception), exception, exception.__traceback__)


class _WrappedPolicy(asyncio.AbstractEventLoopPolicy):
    """包装用户的事件循环策略: 创建 loop 后自动装 TsunTrack 的异常处理器

    继承 AbstractEventLoopPolicy 以满足 set_event_loop_policy 的类型检查;
    其余方法委托给原始策略, 兼容 uvloop / 用户自定义 loop 工厂
    """

    def __init__(self, base_policy, loop_handler) -> None:
        self._base = base_policy
        self._loop_handler = loop_handler

    def new_event_loop(self):
        loop = self._base.new_event_loop()
        try:
            loop.set_exception_handler(self._loop_handler)
        except Exception:
            pass  # 个别 loop 不支持 set_exception_handler, 忽略
        return loop

    def get_event_loop(self):
        return self._base.get_event_loop()

    def set_event_loop(self, loop):
        self._base.set_event_loop(loop)

    def __getattr__(self, name):
        return getattr(self._base, name)
