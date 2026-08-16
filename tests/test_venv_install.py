"""端到端测试：用 uv 创建真实虚拟环境并安装本包，验证 .pth 自动生效。

首次运行需要联网下载依赖（rich、pygments 等）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    shutil.which("uv") is None,
    reason="uv 未安装",
)


def _venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _run(
    command: list[str],
    *,
    timeout: int,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        env=env,
    )


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("TSUNTRACK_CONFIG", None)
    env.pop("PYTHONPATH", None)
    env["PYTHONUTF8"] = "1"
    return env


def test_venv_install_activates_pth_auto_hook(tmp_path):
    env = _clean_env()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    env["HOME"] = str(home_dir)
    if os.name == "nt":
        env["USERPROFILE"] = str(home_dir)

    venv = tmp_path / "venv"
    _run(["uv", "venv", str(venv)], timeout=120, env=env)

    python = _venv_python(venv)
    _run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            str(PROJECT_ROOT),
        ],
        timeout=300,
        env=env,
    )

    site_packages = next(venv.rglob("site-packages"))
    assert (site_packages / "tsuntrack_auto.pth").exists()

    check = subprocess.run(
        [
            str(python),
            "-c",
            "import sys; import tsuntrack; "
            "print(sys.excepthook.__module__); "
            "print(sys.excepthook.__name__)",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        env=env,
    )
    assert check.returncode == 0, check.stderr
    assert "tsuntrack.handler" in check.stdout
    assert "tsuntrack_excepthook" in check.stdout

    result = subprocess.run(
        [str(python), "-c", "raise ValueError('boom')"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        env=env,
    )
    assert result.returncode != 0
    assert "主人" in result.stderr
    assert "boom" in result.stderr
