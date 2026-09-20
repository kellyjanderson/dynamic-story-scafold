#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

run_pipx() {
  if command -v pipx >/dev/null 2>&1; then
    pipx "$@"
    return
  fi
  if python3 -m pipx --version >/dev/null 2>&1; then
    python3 -m pipx "$@"
    return
  fi

  cat >&2 <<'EOF'
DSS installation requires pipx, the standard Python application installer.

On macOS:
  brew install pipx
  pipx ensurepath

Then rerun:
  ./scripts/install.sh
EOF
  exit 1
}

echo "==> Installing Dynamic Story Scaffold with pipx"
run_pipx install --force "$repo_root"

bin_dir=$(run_pipx environment --value PIPX_BIN_DIR)

echo "==> Preparing application state"
"$bin_dir/dss-maintain" setup

echo
echo "Dynamic Story Scaffold installed."
echo "  app:         $bin_dir/dss"
echo "  maintenance: $bin_dir/dss-maintain"
echo
echo "Run: dss --help"
