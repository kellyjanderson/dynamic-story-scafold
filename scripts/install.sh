#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
install_root="${DSS_INSTALL_ROOT:-$HOME/.local/apps/dss}"
bin_dir="${DSS_BIN_DIR:-$HOME/.local/bin}"
releases_dir="$install_root/releases"
release="$releases_dir/$(date +%Y%m%d-%H%M%S)-$$"
venv="$release/.venv"
current="$install_root/current"
cleanup_release=1

cleanup() {
  if [ "$cleanup_release" -eq 1 ]; then
    rm -rf "$release"
  fi
}
trap cleanup 0 HUP INT TERM

echo "==> Building and qualifying Dynamic Story Scaffold"
(
  cd "$repo_root"
  ./scripts/build.sh
)

wheel=$(find "$repo_root/dist" -maxdepth 1 -type f -name '*.whl' -print | sort | tail -n 1)
if [ -z "$wheel" ]; then
  echo "install: no wheel produced under $repo_root/dist" >&2
  exit 1
fi

echo "==> Installing $wheel"
mkdir -p "$releases_dir" "$bin_dir"
python3 -m venv "$venv"
"$venv/bin/python" -m pip install --disable-pip-version-check -q --upgrade pip
"$venv/bin/python" -m pip install --disable-pip-version-check -q "$wheel"

echo "==> Preparing application state"
"$venv/bin/dss-maintain" setup

old_current=$(readlink "$current" 2>/dev/null || true)
ln -sfn "$release" "$current"
ln -sfn "$current/.venv/bin/dss" "$bin_dir/dss"
ln -sfn "$current/.venv/bin/dss-maintain" "$bin_dir/dss-maintain"

cleanup_release=0

case "$old_current" in
  "$releases_dir"/*)
    if [ "$old_current" != "$release" ]; then
      rm -rf "$old_current"
    fi
    ;;
esac

echo
echo "Dynamic Story Scaffold installed."
echo "  app:         $bin_dir/dss"
echo "  maintenance: $bin_dir/dss-maintain"
echo
if command -v dss >/dev/null 2>&1; then
  echo "Run: dss --help"
else
  echo "Add $bin_dir to PATH, then run: dss --help"
fi
