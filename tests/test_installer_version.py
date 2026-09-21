from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_installer_version_matches_package_without_running_install() -> None:
    package_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    result = subprocess.run(
        ["sh", str(ROOT / "scripts" / "install.sh"), "--version"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == f"DSS installer {package_version}"
    assert result.stderr == ""
