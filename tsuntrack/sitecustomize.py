"""由 ``tsuntrack_auto.pth`` 在解释器启动时导入, 自动安装全局异常钩子.

这样就能做到: ``pip install tsuntrack`` 之后, 不需要在业务代码里显式
``import tsuntrack``, 报错也会自动变成傲娇风格.
"""

from __future__ import annotations

import sys


def _auto_install() -> None:
    try:
        from tsuntrack import install

        install()
    except Exception as exc:
        print(
            f"TsunTrack: 自动安装失败（{exc!r}），请检查安装是否完整。", file=sys.stderr
        )


_auto_install()
