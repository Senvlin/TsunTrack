"""集成测试：模拟安装后由 .pth 自动启用 TsunTrack。

通过把 tsuntrack 包和 tsuntrack_auto.pth 复制到临时 site-packages，
再在子进程里手动调用 site.addsitedir()，触发与真实解释器启动一致的 .pth 处理。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PROJECT_ROOT / "tsuntrack"
PTH_FILE = PROJECT_ROOT / "tsuntrack_auto.pth"


def _install_fake_site(site_packages: Path) -> None:
    site_packages.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        PACKAGE_DIR,
        site_packages / "tsuntrack",
        dirs_exist_ok=True,
    )
    shutil.copy2(PTH_FILE, site_packages / "tsuntrack_auto.pth")


def _run_in_installed_env(
    site_packages: Path,
    code: str,
    *,
    cwd: Path | None = None,
    config_text: str | None = None,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if cwd is None:
        cwd = site_packages.parent / "cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    if config_text is not None:
        (cwd / "tsuntrack.toml").write_text(config_text, encoding="utf-8")

    env = os.environ.copy()
    env.pop("TSUNTRACK_CONFIG", None)
    env["PYTHONUTF8"] = "1"
    # 隔离用户目录，避免 ~/.config/tsuntrack/config.toml 影响测试。
    home_dir = site_packages.parent / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(home_dir)
    if os.name == "nt":
        env["USERPROFILE"] = str(home_dir)

    # 子进程使用 -S 启动，不会自动加载当前环境的 site-packages；
    # 这里手动把 fake site-packages 放在最前面，再把当前进程的 rich/pygments
    # 等依赖路径追加进去，保证 .pth 中的 tsuntrack 使用 fake 副本。
    search_paths = [str(site_packages), *[p for p in sys.path if p]]
    env["PYTHONPATH"] = os.pathsep.join(search_paths)
    if env_extra:
        env.update(env_extra)

    # 让子进程 coverage 数据写到项目根目录，这样 pytest-cov 结束时会自动 combine。
    env["COVERAGE_FILE"] = str(PROJECT_ROOT / ".coverage")

    # 子进程使用 -S 启动，不会自动执行 coverage 的 .pth；
    # 这里手动启动 coverage，保证子进程里的 tsuntrack 也能被统计到。
    script = (
        "import sys, site\n"
        "try:\n"
        "    import coverage\n"
        "    coverage.process_startup()\n"
        "except Exception:\n"
        "    pass\n"
        f"site.addsitedir({str(site_packages)!r})\n"
        f"{code}\n"
    )

    return subprocess.run(
        [sys.executable, "-S", "-c", script],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def test_pth_auto_installs_hook(tmp_path):
    site_packages = tmp_path / "site-packages"
    _install_fake_site(site_packages)

    result = _run_in_installed_env(
        site_packages,
        "import tsuntrack\n"
        "print(sys.excepthook.__module__)\n"
        "print(sys.excepthook.__name__)\n",
    )

    assert result.returncode == 0, result.stderr
    assert "tsuntrack.handler" in result.stdout
    assert "tsuntrack_excepthook" in result.stdout


def test_pth_auto_customizes_uncaught_exception(tmp_path):
    site_packages = tmp_path / "site-packages"
    _install_fake_site(site_packages)

    result = _run_in_installed_env(
        site_packages,
        "raise ValueError('boom')",
    )

    assert result.returncode != 0
    assert "主人" in result.stderr
    assert "boom" in result.stderr


def test_pth_respects_cwd_config_override(tmp_path):
    site_packages = tmp_path / "site-packages"
    cwd = tmp_path / "cwd"
    _install_fake_site(site_packages)

    result = _run_in_installed_env(
        site_packages,
        "raise ValueError('boom')",
        cwd=cwd,
        config_text=(
            '[exceptions.ValueError]\ntemplate = "集成测试自定义: {message}"\n'
        ),
    )

    assert result.returncode != 0
    assert "集成测试自定义: boom" in result.stderr


def test_pth_respects_env_config_override(tmp_path):
    site_packages = tmp_path / "site-packages"
    config_file = tmp_path / "custom-config.toml"
    config_file.write_text(
        '[exceptions.ValueError]\ntemplate = "环境变量配置: {message}"\n',
        encoding="utf-8",
    )
    _install_fake_site(site_packages)

    result = _run_in_installed_env(
        site_packages,
        "raise ValueError('boom')",
        env_extra={"TSUNTRACK_CONFIG": str(config_file)},
    )

    assert result.returncode != 0
    assert "环境变量配置: boom" in result.stderr


def test_pth_disabled_keeps_default_hook(tmp_path):
    site_packages = tmp_path / "site-packages"
    cwd = tmp_path / "cwd"
    _install_fake_site(site_packages)

    result = _run_in_installed_env(
        site_packages,
        "import tsuntrack\nprint(sys.excepthook is sys.__excepthook__)\n",
        cwd=cwd,
        config_text="[general]\nenabled = false\n",
    )

    assert result.returncode == 0, result.stderr
    assert "True" in result.stdout
