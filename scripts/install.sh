#!/bin/sh
set -eu

installer_version=0.1.0

case ${1-} in
  --version)
    printf 'DSS installer %s\n' "$installer_version"
    exit 0
    ;;
  '') ;;
  *)
    printf 'Usage: %s [--version]\n' "$0" >&2
    exit 2
    ;;
esac

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

  if command -v brew >/dev/null 2>&1; then
    echo "==> Installing pipx with Homebrew"
    brew install pipx
    pipx ensurepath >/dev/null 2>&1 || true
    pipx "$@"
    return
  fi

  cat >&2 <<'EOF'
DSS installation requires pipx, the standard Python application installer.
Install pipx with your OS package manager, then rerun ./scripts/install.sh.
EOF
  exit 1
}

echo "==> Installing Dynamic Story Scaffold with pipx (installer $installer_version)"
run_pipx install --force "$repo_root"
run_pipx ensurepath >/dev/null 2>&1 || true

bin_dir=$(run_pipx environment --value PIPX_BIN_DIR)

echo "==> Preparing application state"
"$bin_dir/dss-maintain" setup

echo
echo "Dynamic Story Scaffold installed."
echo "  app:         $bin_dir/dss"
echo "  maintenance: $bin_dir/dss-maintain"
echo
if command -v dss >/dev/null 2>&1; then
  echo "Run: dss --help"
else
  echo "Restart your shell once so pipx's app directory is on PATH, then run: dss --help"
fi
