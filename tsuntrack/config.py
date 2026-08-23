"""配置加载与合并

查找顺序(优先级从高到低):

1. 环境变量 ``TSUNTRACK_CONFIG`` 指定的路径
2. 当前工作目录下的 ``tsuntrack.toml``
3. 用户主目录 ``~/.config/tsuntrack/config.toml``
4. 包内置 ``defaults.toml``
"""

from __future__ import annotations

import os
import tomllib
import warnings
from pathlib import Path
from typing import Any

ENV_VAR = "TSUNTRACK_CONFIG"
CWD_FILE = "tsuntrack.toml"
USER_CONFIG_REL = Path(".config") / "tsuntrack" / "config.toml"
DEFAULTS_FILE = "defaults.toml"
LOCALES_DIR = Path(__file__).with_name("locales")
DEFAULT_LANGUAGE = "zh"

_cache: dict[str, Any] | None = None


def _defaults() -> dict[str, Any]:
    """读取包内置的 defaults.toml"""
    path = Path(__file__).with_name(DEFAULTS_FILE)
    with path.open("rb") as f:
        return tomllib.load(f)


def _load_locale(language: str) -> dict[str, Any]:
    """读取内置语言文件 ``locales/{language}.toml``; 找不到时回退默认语言, 仍失败返回 {}

    :param language: ``[general] language`` 的值, 如 ``zh`` / ``en``
    """
    path = LOCALES_DIR / f"{language}.toml"
    if not path.is_file():
        if language != DEFAULT_LANGUAGE:
            warnings.warn(
                f"TsunTrack: locale '{language}' not found, "
                f"falling back to '{DEFAULT_LANGUAGE}'.",
            )
        path = LOCALES_DIR / f"{DEFAULT_LANGUAGE}.toml"
    if not path.is_file():
        warnings.warn(
            f"TsunTrack: default locale '{DEFAULT_LANGUAGE}' not found, language support disabled."
        )
        return {}
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        warnings.warn(
            f"TsunTrack: locale file {path} failed to load ({exc}), skipped.",
        )
        return {}


def _candidates() -> list[Path]:
    """按优先级返回候选配置文件路径(不保证都存在)"""
    paths: list[Path] = []
    env = os.environ.get(ENV_VAR)
    if env:
        env_path = Path(env)
        if env_path.is_file():
            paths.append(env_path)
        else:
            warnings.warn(
                f"TsunTrack: env var {ENV_VAR} points to a missing file: "
                f"{env_path}, ignored.",
            )
    paths.append(Path.cwd() / CWD_FILE)
    paths.append(Path.home() / USER_CONFIG_REL)
    return paths


def _deep_merge(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    merged = dict(base)

    for key, value in override.items():
        # 只有当 value 本身是字典时，才需要考虑递归合并
        if isinstance(value, dict):
            existing = merged.get(key)
            if isinstance(existing, dict):
                merged[key] = _deep_merge(existing, value)
                continue
        merged[key] = value

    return merged


def _without_theme(cfg: dict[str, Any]) -> dict[str, Any]:
    """去掉配置里的 ``theme`` 主题容器键(运行时不需要它)"""
    return {k: v for k, v in cfg.items() if k != "theme"}


def load_config(use_cache: bool = True) -> dict[str, Any]:
    """加载配置: 基础层 + 主题覆盖层 + 用户配置层, 返回合并结果"""
    global _cache
    if use_cache and _cache is not None:
        return _cache

    defaults = _defaults()

    user = {}
    for path in reversed(_candidates()):
        if not path.is_file():
            continue
        try:
            with path.open("rb") as f:
                user_cfg = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            warnings.warn(
                f"TsunTrack: failed to read config file {path} ({exc}), skipped."
            )
            continue
        user = _deep_merge(user, user_cfg)

    language = (user.get("general") or {}).get("language") or (
        defaults.get("general") or {}
    ).get("language", DEFAULT_LANGUAGE)
    locale = _load_locale(language)

    theme_name = (user.get("general") or {}).get("theme") or (
        defaults.get("general") or {}
    ).get("theme", "")

    base = _deep_merge(_without_theme(defaults), _without_theme(locale))

    if theme_name:
        theme_overrides = {}
        locale_theme = locale.get("theme", {}).get(theme_name)
        if locale_theme:
            theme_overrides = _deep_merge(theme_overrides, locale_theme)
        user_theme = user.get("theme", {}).get(theme_name)
        if user_theme:
            theme_overrides = _deep_merge(theme_overrides, user_theme)
        if theme_overrides:
            base = _deep_merge(base, theme_overrides)

    # 用户配置（非主题部分）最后覆盖
    merged = _deep_merge(base, _without_theme(user))

    _cache = merged
    return _cache


def reload_config() -> dict[str, Any]:
    """清除缓存并重新加载配置(配置文件改动后调用生效)"""
    global _cache
    _cache = None
    return load_config()
