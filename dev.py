from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"

# Development commands operate directly from the checkout before the package
# is necessarily installed.
sys.path.insert(0, str(SRC))

from dynamic_story_scaffold.builds import BuildManager  # noqa: E402


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def test() -> None:
    run(sys.executable, "-m", "pytest", "-q")


def package() -> Path:
    record = BuildManager().build(
        project_root=ROOT,
        output_dir=DIST,
        clean=True,
    )
    wheels = [
        artifact.path
        for artifact in record.artifacts
        if artifact.kind == "wheel"
    ]
    if len(wheels) != 1:
        raise RuntimeError(
            f"expected exactly one wheel from build {record.id}, found {len(wheels)}"
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
    """Qualification build: run tests, then create tracked wheel and sdist."""
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
