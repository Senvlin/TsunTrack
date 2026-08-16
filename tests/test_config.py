"""配置测试：纯函数 + 配置加载/缓存/重载。
"""

from pathlib import Path

import tsuntrack.config as config
from tsuntrack.config import _deep_merge, _without_theme, load_config, reload_config


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
    monkeypatch.setattr(config, "_candidates", lambda: [])

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
    monkeypatch.setattr(config, "_candidates", lambda: [user_file])

    cfg = load_config(use_cache=False)

    assert cfg["exceptions"]["ValueError"]["template"] == "user-override"
    assert cfg["exceptions"]["default"]["template"] == "default"


def test_load_config_applies_theme_override(monkeypatch):
    monkeypatch.setattr(config, "_cache", None)
    monkeypatch.setattr(
        config,
        "_defaults",
        lambda: {
            "general": {"theme": "neko"},
            "theme": {
                "neko": {"exceptions": {"default": {"template": "neko-default"}}},
            },
            "exceptions": {"default": {"template": "base-default"}},
        },
    )
    monkeypatch.setattr(config, "_candidates", lambda: [])

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
            "theme": {
                "neko": {"exceptions": {"default": {"template": "neko-default"}}},
            },
            "exceptions": {"default": {"template": "base-default"}},
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
    monkeypatch.setattr(config, "_candidates", lambda: [])

    first = load_config(use_cache=True)
    second = load_config(use_cache=True)

    assert first is second
    assert calls == ["defaults"]

    third = reload_config()

    assert third is not first
    assert calls == ["defaults", "defaults"]



def test_candidates_warns_when_env_config_missing(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "missing.toml"
    monkeypatch.setenv("TSUNTRACK_CONFIG", str(missing))
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    paths = config._candidates()

    assert missing not in paths
    assert tmp_path / "tsuntrack.toml" in paths
    assert tmp_path / ".config" / "tsuntrack" / "config.toml" in paths
    assert "指向的文件不存在" in capsys.readouterr().err
