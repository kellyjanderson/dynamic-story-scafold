#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
install_root="${DSS_INSTALL_ROOT:-$HOME/.local/apps/dss}"
bin_dir="${DSS_BIN_DIR:-$HOME/.local/bin}"
venv="$install_root/.venv"
staging="$install_root/.venv.new"
backup="$install_root/.venv.old"

echo "==> Building and qualifying Dynamic Story Scaffold"
(
  cd "$repo_root"
  /bin/sh scripts/automation-hatch run build
)

wheel=$(find "$repo_root/dist" -maxdepth 1 -type f -name '*.whl' -print | sort | tail -n 1)
if [ -z "$wheel" ]; then
  echo "install: no wheel produced under $repo_root/dist" >&2
  exit 1
fi

echo "==> Installing $wheel"
mkdir -p "$install_root" "$bin_dir"
rm -rf "$staging"
python3 -m venv "$staging"
"$staging/bin/python" -m pip install --disable-pip-version-check -q --upgrade pip
"$staging/bin/python" -m pip install --disable-pip-version-check -q "$wheel"

echo "==> Preparing application state"
"$staging/bin/dss-maintain" setup

rm -rf "$backup"
if [ -d "$venv" ]; then
  mv "$venv" "$backup"
fi
if ! mv "$staging" "$venv"; then
  if [ -d "$backup" ]; then
    mv "$backup" "$venv"
  fi
  exit 1
fi
rm -rf "$backup"

ln -sfn "$venv/bin/dss" "$bin_dir/dss"
ln -sfn "$venv/bin/dss-maintain" "$bin_dir/dss-maintain"

echo
echo "Dynamic Story Scaffold installed."
echo "  app:        $bin_dir/dss"
echo "  maintenance: $bin_dir/dss-maintain"
echo
if command -v dss >/dev/null 2>&1; then
  echo "Run: dss --help"
else
  echo "Add $bin_dir to PATH, then run: dss --help"
fi
