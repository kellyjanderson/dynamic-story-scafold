#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

echo "==> Running tests"
/bin/sh scripts/automation-hatch run pytest -q

echo "==> Building distribution artifacts"
/bin/sh scripts/automation-hatch build -c

echo "==> Recording build manifest"
/bin/sh scripts/automation-hatch run python scripts/record_build.py dist
