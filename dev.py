from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def clean_dist() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)


def test() -> None:
    run(sys.executable, "-m", "pytest", "-q")


def package() -> Path:
    clean_dist()
    run(sys.executable, "-m", "build", "--outdir", str(DIST), str(ROOT))

    wheels = sorted(DIST.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            f"expected exactly one wheel in {DIST}, found {len(wheels)}"
        )
    return wheels[0]


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


def build() -> None:
    """Qualification build: run tests, then create wheel and sdist."""
    test()
    package()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Development commands for Dynamic Story Scaffold."
    )
    parser.add_argument(
        "command",
        choices=("test", "build", "package", "install"),
    )
    args = parser.parse_args()

    commands = {
        "test": test,
        "build": build,
        "package": package,
        "install": install,
    }
    commands[args.command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
