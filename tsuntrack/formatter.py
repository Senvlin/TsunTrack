"""根据异常类型与配置模板, 生成最终的报错文本"""

from __future__ import annotations

import re
from typing import Any

from . import config as _config

DEFAULT_TEMPLATE = "{exc_type}: {message}"

_NAME_FROM_MESSAGE = [
    re.compile(r"name '(?P<name>[^']+)' is not defined"),
    re.compile(r"cannot access local variable '(?P<name>[^']+)'"),
    re.compile(r"local variable '(?P<name>[^']+)' referenced before assignment"),
    re.compile(r"'(?P<name>[^']+)' is not defined"),
    re.compile(r"object has no attribute '(?P<name>[^']+)'"),
]


class _SafeDict(dict[str, Any]):
    """模板里出现未知占位符时原样保留, 而不是抛 KeyError"""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _safe_str(exc_value: BaseException | None) -> str:
    """安全地取异常消息文本(个别异常 __str__ 可能抛错)"""
    if exc_value is None:
        return ""
    try:
        return str(exc_value)
    except Exception:
        return ""


def _extract_name(exc_type: type[BaseException], exc_value: BaseException) -> str:
    """提取模板 {name} 使用的名称: NameError 的变量名 / AttributeError 的属性名 /
    ModuleNotFoundError 的模块名 / KeyError 的键 / OSError 系(FileNotFoundError 等)的文件名."""
    name = getattr(exc_value, "name", None)
    if name is not None:
        return str(name)

    # OSError 系(FileNotFoundError / PermissionError 等): filename 是缺失/出问题的文件名
    filename = getattr(exc_value, "filename", None)
    if filename is not None:
        return str(filename)
    # 单参数构造(如 FileNotFoundError("foo.txt"))时 filename 属性为 None,
    # 但 args[0] 就是那个文件名(多参数时 args[0] 是 int errno, 会被过滤掉)
    if (
        isinstance(exc_value, OSError)
        and exc_value.args
        and isinstance(exc_value.args[0], str)
    ):
        return exc_value.args[0]

    if isinstance(exc_value, KeyError) and exc_value.args:
        first = exc_value.args[0]
        return first if isinstance(first, str) else repr(first)

    message = _safe_str(exc_value)
    for pattern in _NAME_FROM_MESSAGE:
        match = pattern.search(message)
        if match:
            return match.group("name")
    return ""


def build_context(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb,
) -> dict[str, Any]:
    """从异常对象与回溯对象中提取模板可用的全部字段"""
    ctx: dict[str, Any] = {
        "exc_type": getattr(exc_type, "__name__", str(exc_type)),
        "message": _safe_str(exc_value),
        "name": "",
        "exc_filename": "",
        "filename": "",
        "lineno": 0,
        "func_name": "",
        "module": "",
    }

    ctx["name"] = _extract_name(exc_type, exc_value)

    # OSError 系(FileNotFoundError 等)的文件名, 与栈帧路径 {filename} 区分
    exc_filename = getattr(exc_value, "filename", None)
    if exc_filename is None:
        exc_filename = getattr(exc_value, "filename2", None)
    if exc_filename is not None:
        ctx["exc_filename"] = str(exc_filename)

    # 取最内层(离异常最近)的栈帧信息
    frame = exc_tb
    while frame is not None and frame.tb_next is not None:
        frame = frame.tb_next
    if frame is not None:
        code = frame.tb_frame.f_code
        ctx["filename"] = code.co_filename
        ctx["lineno"] = frame.tb_lineno
        ctx["func_name"] = code.co_name
        ctx["module"] = frame.tb_frame.f_globals.get("__name__", "") or ""

    return ctx


def resolve_exception_config(cfg: dict[str, Any], exc_name: str) -> dict[str, Any]:
    """按异常类型名取模板配置, 找不到就回退到 exceptions.default"""
    exceptions = cfg.get("exceptions") or {}
    exc_cfg = exceptions.get(exc_name)
    if not isinstance(exc_cfg, dict):
        exc_cfg = exceptions.get("default") or {}
    return exc_cfg if isinstance(exc_cfg, dict) else {}


def format_message(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb,
    cfg: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """生成 (消息文本, 样式)

    :param cfg: 合并后的配置; 为 None 时内部自动加载
    :param extra: 额外占位符, 会合并进模板上下文(自定义占位符的入口)
    """
    if cfg is None:
        cfg = _config.load_config()
    exc_name = getattr(exc_type, "__name__", str(exc_type))
    exc_cfg = resolve_exception_config(cfg, exc_name)
    template = exc_cfg.get("template") or DEFAULT_TEMPLATE

    ctx = build_context(exc_type, exc_value, exc_tb)
    if extra:
        ctx.update(extra)
    message = template.format_map(_SafeDict(ctx))
    return message
