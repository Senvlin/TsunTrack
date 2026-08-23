"""配置测试：纯函数 + 配置加载/缓存/重载。"""

from pathlib import Path

from tsuntrack import config
from tsuntrack.config import (
    _deep_merge,
    _without_theme,
    load_config,
    reload_config,
)


def test_deep_merge_overrides_scalar_and_merges_nested():
    base = {
        "general": {"enabled": True, "max_frames": 5},
        "exceptions": {"default": {"template": "old"}},
    }
    override = {
        "general": {"enabled": False},
        "exceptions": {"NameError": {"template": "new"}},
    }

    merged = _deep_merge(base, override)

    assert merged == {
        "general": {"enabled": False, "max_frames": 5},
        "exceptions": {
            "default": {"template": "old"},
            "NameError": {"template": "new"},
        },
    }


def test_deep_merge_non_dict_override_replaces_dict():
    base = {"general": {"enabled": True}}
    override = {"general": False}

    merged = _deep_merge(base, override)

    assert merged == {"general": False}


def test_deep_merge_adds_new_nested_keys():
    base = {"exceptions": {"default": {"template": "x"}}}
    override = {"exceptions": {"ValueError": {"template": "y"}}}

    merged = _deep_merge(base, override)

    assert merged == {
        "exceptions": {
            "default": {"template": "x"},
            "ValueError": {"template": "y"},
        }
    }


def test_deep_merge_empty_override_returns_new_top_level_dict():
    base = {"a": {"b": 1}}

    merged = _deep_merge(base, {})

    assert merged == base
    assert merged is not base


def test_without_theme_removes_only_theme_key():
    cfg = {
        "general": {"enabled": True},
        "theme": {"neko": {"exceptions": {"default": {"template": "x"}}}},
        "exceptions": {"default": {"template": "y"}},
    }

    assert _without_theme(cfg) == {
        "general": {"enabled": True},
        "exceptions": {"default": {"template": "y"}},
    }


def test_without_theme_returns_new_dict():
    cfg = {"theme": {"neko": {}}}

    result = _without_theme(cfg)

    assert result == {}
    assert result is not cfg


def test_deep_merge_does_not_mutate_base():
    base = {"general": {"enabled": True, "max_frames": 5}}
    override = {"general": {"enabled": False}}

    _deep_merge(base, override)

    assert base == {"general": {"enabled": True, "max_frames": 5}}


def test_without_theme_does_not_mutate_original():
    cfg = {
        "general": {"enabled": True},
        "theme": {"neko": {}},
    }

    _without_theme(cfg)

    assert cfg == {
        "general": {"enabled": True},
        "theme": {"neko": {}},
    }


def test_load_config_uses_defaults_when_no_user_config(monkeypatch):
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: {
            "general": {"enabled": True, "theme": "neko"},
            "exceptions": {"default": {"template": "default"}},
        },
    )
    monkeypatch.setattr(config, "_load_locale", lambda language: {})
    monkeypatch.setattr(config, "_candidates", list)

    cfg = load_config(use_cache=False)

    assert cfg["general"]["enabled"] is True
    assert cfg["exceptions"]["default"]["template"] == "default"


def test_load_config_applies_user_override(monkeypatch, tmp_path):
    user_file = tmp_path / "user.toml"
    user_file.write_text(
        '[exceptions.ValueError]\ntemplate = "user-override"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: {
            "general": {"theme": "neko"},
            "exceptions": {"default": {"template": "default"}},
        },
    )
    monkeypatch.setattr(config, "_load_locale", lambda language: {})
    monkeypatch.setattr(config, "_candidates", lambda: [user_file])

    cfg = load_config(use_cache=False)

    assert cfg["exceptions"]["ValueError"]["template"] == "user-override"
    assert cfg["exceptions"]["default"]["template"] == "default"


def test_load_config_applies_theme_override(monkeypatch):
    """主题覆盖: 主题内容来自语言层, 选中后覆盖基础配置"""
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: {
            "general": {"theme": "neko"},
            "exceptions": {"default": {"template": "base-default"}},
        },
    )
    monkeypatch.setattr(
        config,
        "_load_locale",
        lambda language: {
            "theme": {
                "neko": {
                    "exceptions": {"default": {"template": "neko-default"}}
                },
            },
        },
    )
    monkeypatch.setattr(config, "_candidates", list)

    cfg = load_config(use_cache=False)

    assert cfg["exceptions"]["default"]["template"] == "neko-default"


def test_load_config_user_overrides_theme(monkeypatch, tmp_path):
    user_file = tmp_path / "user.toml"
    user_file.write_text(
        '[exceptions.default]\ntemplate = "user-default"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: {
            "general": {"theme": "neko"},
            "exceptions": {"default": {"template": "base-default"}},
        },
    )
    monkeypatch.setattr(
        config,
        "_load_locale",
        lambda language: {
            "theme": {
                "neko": {
                    "exceptions": {"default": {"template": "neko-default"}}
                },
            },
        },
    )
    monkeypatch.setattr(config, "_candidates", lambda: [user_file])

    cfg = load_config(use_cache=False)

    assert cfg["exceptions"]["default"]["template"] == "user-default"


def test_load_config_ignores_invalid_user_file(monkeypatch, tmp_path):
    bad_file = tmp_path / "bad.toml"
    bad_file.write_text("this is not [valid toml", encoding="utf-8")
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: {"general": {"enabled": True}},
    )
    monkeypatch.setattr(config, "_load_locale", lambda language: {})
    monkeypatch.setattr(config, "_candidates", lambda: [bad_file])

    cfg = load_config(use_cache=False)

    assert cfg["general"]["enabled"] is True


def test_load_config_caches_and_reload_clears_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: calls.append("defaults") or {"general": {"enabled": True}},
    )
    monkeypatch.setattr(config, "_load_locale", lambda language: {})
    monkeypatch.setattr(config, "_candidates", list)

    first = load_config(use_cache=True)
    second = load_config(use_cache=True)

    assert first is second
    assert calls == ["defaults"]

    third = reload_config()

    assert third is not first
    assert calls == ["defaults", "defaults"]


def test_candidates_warns_when_env_config_missing(
    monkeypatch, tmp_path, capsys
):
    missing = tmp_path / "missing.toml"
    monkeypatch.setenv("TSUNTRACK_CONFIG", str(missing))
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    paths = config._candidates()

    assert missing not in paths
    assert tmp_path / "tsuntrack.toml" in paths
    assert tmp_path / ".config" / "tsuntrack" / "config.toml" in paths
    assert "points to a missing file" in capsys.readouterr().err


def test_load_config_applies_locale_layer(monkeypatch):
    """语言层: [general] language 决定加载哪个 locale, locale 与 defaults 深合并"""
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: {
            "general": {"language": "en"},
            "hints": {"aliases": {"PIL": "pillow"}},
        },
    )
    loaded = []

    def fake_load_locale(language):
        loaded.append(language)
        return {
            "hints": {"NameError": {"template": "Did you mean {did_you_mean}?"}}
        }

    monkeypatch.setattr(config, "_load_locale", fake_load_locale)
    monkeypatch.setattr(config, "_candidates", list)

    cfg = load_config(use_cache=False)

    assert loaded == ["en"]
    assert (
        cfg["hints"]["NameError"]["template"] == "Did you mean {did_you_mean}?"
    )
    # locale 的 [hints.*] 与 defaults 的 [hints.aliases] 共存
    assert cfg["hints"]["aliases"]["PIL"] == "pillow"


def test_load_config_user_language_wins(monkeypatch, tmp_path):
    """用户配置里的 language 优先于 defaults"""
    user_file = tmp_path / "user.toml"
    user_file.write_text('[general]\nlanguage = "en"\n', encoding="utf-8")
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: {"general": {"language": "zh"}},
    )
    loaded = []
    monkeypatch.setattr(
        config,
        "_load_locale",
        lambda language: loaded.append(language) or {},
    )
    monkeypatch.setattr(config, "_candidates", lambda: [user_file])

    load_config(use_cache=False)

    assert loaded == ["en"]


def test_load_config_user_overrides_locale(monkeypatch, tmp_path):
    """用户配置压过语言层(部分覆盖)"""
    user_file = tmp_path / "user.toml"
    user_file.write_text(
        '[hints.NameError]\ntemplate = "my custom: {name}"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: {"general": {"language": "en"}},
    )
    monkeypatch.setattr(
        config,
        "_load_locale",
        lambda language: {
            "hints": {"NameError": {"template": "locale: {name}"}}
        },
    )
    monkeypatch.setattr(config, "_candidates", lambda: [user_file])

    cfg = load_config(use_cache=False)

    assert cfg["hints"]["NameError"]["template"] == "my custom: {name}"


def test_load_locale_selects_and_falls_back(monkeypatch, tmp_path, capsys):
    """_load_locale: 命中语言文件 / 未知语言回退默认并警告"""
    locales = tmp_path / "locales"
    locales.mkdir()
    (locales / "zh.toml").write_text(
        '[hints.NameError]\ntemplate = "zh-hint"\n', encoding="utf-8"
    )
    (locales / "en.toml").write_text(
        '[hints.NameError]\ntemplate = "en-hint"\n', encoding="utf-8"
    )
    monkeypatch.setattr(config, "LOCALES_DIR", locales)

    zh = config._load_locale("zh")
    en = config._load_locale("en")
    fr = config._load_locale("fr")

    assert zh["hints"]["NameError"]["template"] == "zh-hint"
    assert en["hints"]["NameError"]["template"] == "en-hint"
    assert fr["hints"]["NameError"]["template"] == "zh-hint"  # 回退默认语言
    assert "falling back" in capsys.readouterr().err


def test_load_locale_missing_files_return_empty(monkeypatch, tmp_path):
    """_load_locale: 连默认语言文件都没有时返回 {}"""
    locales = tmp_path / "locales"
    locales.mkdir()
    monkeypatch.setattr(config, "LOCALES_DIR", locales)

    assert config._load_locale("zh") == {}
