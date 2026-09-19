from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"

sys.path.insert(0, str(SRC))

from dynamic_story_scaffold.database import Database  # noqa: E402


def run(*args: str, capture: bool = False):
    return subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )


def test() -> None:
    run(sys.executable, "-m", "pytest", "-q")


def _git(*args: str) -> str | None:
    try:
        return run("git", *args, capture=True).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def package() -> Path:
    if DIST.exists():
        shutil.rmtree(DIST)

    run(sys.executable, "-m", "build", "--outdir", str(DIST), str(ROOT))

    wheels = sorted(DIST.glob("*.whl"))
    sdists = sorted(DIST.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError("expected exactly one wheel and one source distribution")

    with (ROOT / "pyproject.toml").open("rb") as handle:
        version = str(tomllib.load(handle)["project"]["version"])

    artifacts = []
    for path in [*wheels, *sdists]:
        kind = "wheel" if path.suffix == ".whl" else "sdist"
        artifacts.append((kind, path.resolve(), path.stat().st_size, _sha256(path)))

    Database().record_build(
        package_version=version,
        project_root=ROOT,
        output_dir=DIST,
        git_commit=_git("rev-parse", "HEAD"),
        git_branch=_git("branch", "--show-current"),
        artifacts=artifacts,
    )
    return wheels[0]


def build() -> None:
    test()
    package()


def install() -> None:
    wheel = package()
    run(
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--force-reinstall",
        str(wheel),
    )
    run(sys.executable, "-m", "dynamic_story_scaffold", "install")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("test", "build", "package", "install"))
    args = parser.parse_args()
    {"test": test, "build": build, "package": package, "install": install}[args.command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
