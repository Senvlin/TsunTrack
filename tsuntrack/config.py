"""配置加载与合并。

查找顺序（优先级从高到低）：

1. 环境变量 ``TSUNTRACK_CONFIG`` 指定的路径
2. 当前工作目录下的 ``tsuntrack.toml``
3. 用户主目录 ``~/.config/tsuntrack/config.toml``
4. 包内置 ``defaults.toml``

合并规则（三层，从低到高）：

- 基础配置：defaults.toml 中除 ``[theme.*]`` 之外的内容（所有主题共用）
- 主题覆盖：按 ``[general] theme`` 选中的 ``[theme."主题名".*]`` 覆盖基础配置
- 用户配置：用户文件最后合并，可以覆盖上面的任何内容

因此用户可以：
1. 直接覆盖 ``[exceptions.NameError]`` 等任意配置（用户 > 主题 > 基础）
2. 通过 ``[general] theme = "xxx"`` 一键切换内置主题
3. 在用户文件里新增自己的 ``[theme."我的主题".*]`` 自定义主题

结果会被缓存，修改配置文件后调用 :func:`reload_config` 重新读取。
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

ENV_VAR = "TSUNTRACK_CONFIG"
CWD_FILE = "tsuntrack.toml"
USER_CONFIG_REL = Path(".config") / "tsuntrack" / "config.toml"
DEFAULTS_FILE = "defaults.toml"

_cache: dict[str, Any] | None = None


def _defaults() -> dict[str, Any]:
    """读取包内置的 defaults.toml"""
    path = Path(__file__).with_name(DEFAULTS_FILE)
    with path.open("rb") as f:
        return tomllib.load(f)


def _candidates() -> list[Path]:
    """按优先级返回候选配置文件路径(不保证都存在)"""
    paths: list[Path] = []
    env = os.environ.get(ENV_VAR)
    if env:
        env_path = Path(env)
        if env_path.is_file():
            paths.append(env_path)
        else:
            print(
                f"TsunTrack: 环境变量 {ENV_VAR} 指向的文件不存在：{env_path}，已忽略。",
                file=sys.stderr,
            )
    paths.append(Path.cwd() / CWD_FILE)
    paths.append(Path.home() / USER_CONFIG_REL)
    return paths


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归合并两个字典：override 覆盖 base，子字典逐层合并(支持部分覆盖)"""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _without_theme(cfg: dict[str, Any]) -> dict[str, Any]:
    """去掉配置里的 ``theme`` 主题容器键（运行时不需要它）。"""
    return {k: v for k, v in cfg.items() if k != "theme"}


def load_config(use_cache: bool = True) -> dict[str, Any]:
    """加载配置：基础层 + 主题覆盖层 + 用户配置层，返回合并结果。

    :param use_cache: 是否使用模块级缓存(默认使用)
    """
    global _cache
    if use_cache and _cache is not None:
        return _cache

    defaults = _defaults()

    # 1) 用户配置逐层合并（拿到用户改过的 theme / 自定义主题 / 覆盖项）
    user: dict[str, Any] = {}
    for path in _candidates():
        if not path.is_file():
            continue  # 该优先级下没有配置文件，继续往下找
        try:
            with path.open("rb") as f:
                user_cfg = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            print(
                f"TsunTrack: 配置文件 {path} 读取失败（{exc}），已跳过。",
                file=sys.stderr,
            )
            continue
        user = _deep_merge(user, user_cfg)

    # 2) 确定当前主题名：用户配置优先，否则内置默认
    theme_name = (user.get("general") or {}).get("theme") or (
        defaults.get("general") or {}
    ).get("theme", "")

    # 3) 主题覆盖层：内置主题 + 用户自定义主题，按主题名选择
    themes = _deep_merge(defaults.get("theme") or {}, user.get("theme") or {})
    theme_cfg = themes.get(theme_name) if theme_name else None
    base = _without_theme(defaults)
    if isinstance(theme_cfg, dict):
        base = _deep_merge(base, theme_cfg)

    # 4) 用户配置最后合并：用户 > 主题 > 基础
    merged = _deep_merge(base, _without_theme(user))

    _cache = merged
    return _cache


def reload_config() -> dict[str, Any]:
    """清除缓存并重新加载配置(配置文件改动后调用生效)"""
    global _cache
    _cache = None
    return load_config()
