"""智能提示：根据异常类型生成给开发者的实用建议。

- pip install 提示（ModuleNotFoundError / ImportError，支持 PyPI 别名映射）
- did you mean 相近名称建议（NameError / AttributeError，difflib 模糊匹配）

配置见 defaults.toml 的 [hints] 段（基础层，所有主题共用）：
主题层 [theme."X".hints.*] 可覆盖基础提示（复用三层配置合并，自动生效）。
[general] show_hints 是全局开关。
"""

from __future__ import annotations

import difflib
from typing import Any

from . import config as _config
from .formatter import ExceptionContext, _SafeDict, build_context


def _pip_name(name: str, cfg: dict[str, Any]) -> str:
    """模块名 → PyPI 包名（别名表优先，否则原样返回）。"""
    if not name:
        return ""
    aliases = (cfg.get("hints") or {}).get("aliases") or {}
    return aliases.get(name, name)


def _did_you_mean(exc_type: type[BaseException], exc_value: BaseException) -> str:
    """找最接近的已定义名称：NameError 查变量/内建，AttributeError 查对象属性。"""
    name = getattr(exc_value, "name", None)
    if not name:
        return ""

    if issubclass(exc_type, NameError):
        candidates: set[str] = set()
        tb = getattr(exc_value, "__traceback__", None)
        if tb is not None:
            # 沿 tb_next 走到最内层（异常抛出点）的帧，那里才有可见的局部变量
            frame = tb
            while frame.tb_next is not None:
                frame = frame.tb_next
            frame = frame.tb_frame
            candidates.update(frame.f_locals)
            candidates.update(frame.f_globals)
        candidates.update(dir(__builtins__))
        matches = difflib.get_close_matches(name, candidates, n=1)
        return matches[0] if matches else ""

    if issubclass(exc_type, AttributeError):
        obj = getattr(exc_value, "obj", None)
        if obj is not None:
            matches = difflib.get_close_matches(name, dir(obj), n=1)
            return matches[0] if matches else ""

    return ""


def build_hint(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb,
    cfg: dict[str, Any] | None = None,
):
    """生成提示正文(不含 "Hint:" 前缀), 没有合适提示时返回 None

    模板里的 {pip_name} 会被解析成 PyPI 包名, {did_you_mean} 解析成相近名称
    若没有相近名称，整条提示不显示
    """
    if cfg is None:
        cfg = _config.load_config()
    if not (cfg.get("general") or {}).get("show_hints", True):
        return None

    exc_name = getattr(exc_type, "__name__", str(exc_type))
    hint_cfg = (cfg.get("hints") or {}).get(exc_name)
    if not isinstance(hint_cfg, dict) or not hint_cfg.get("template"):
        return None

    template = hint_cfg["template"]
    ctx: ExceptionContext = build_context(exc_type, exc_value, exc_tb)

    if "pip_name" in template:
        ctx["pip_name"] = _pip_name(ctx["name"], cfg)
    if "did_you_mean" in template:
        suggestion = _did_you_mean(exc_type, exc_value)
        if not suggestion:
            return None
        ctx["did_you_mean"] = suggestion

    return template.format_map(_SafeDict(ctx))
