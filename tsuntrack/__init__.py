"""TsunTrack —— 让 Python 的报错变得傲娇起来.

安装后无需在代码里显式 import:
``tsuntrack_auto.pth`` 会在解释器启动时自动导入 ``tsuntrack.sitecustomize``,
从而安装全局异常钩子; 报错文本由配置文件(TOML)驱动, 默认内置傲娇模板.

也可以手动启用:

    import tsuntrack
    tsuntrack.install()
"""

from __future__ import annotations

__version__ = "0.2.1"

__all__ = ["__version__", "install", "uninstall"]


def install() -> bool:
    """安装全局异常钩子(幂等, 可重复调用).

    返回 True 表示钩子已生效; 若配置中 ``[general] enabled = false`` 则返回 False.
    """
    from .handler import install as _install

    return _install()


def uninstall() -> None:
    """卸载全局异常钩子, 恢复安装前的行为."""
    from .handler import uninstall as _uninstall

    _uninstall()
