from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_path

APP_NAME = "dynamic-story-scaffold"
DATA_DIR_ENV = "DYNAMIC_STORY_SCAFFOLD_DATA_DIR"
DATABASE_NAME = "story-scaffold.sqlite3"


def data_dir(*, ensure_exists: bool = False) -> Path:
    """Return the per-user application data directory for this OS.

    Override with DYNAMIC_STORY_SCAFFOLD_DATA_DIR for portable installs, CI,
    tests, or managed deployments.
    """

    override = os.environ.get(DATA_DIR_ENV)
    if override:
        path = Path(override).expanduser()
        if ensure_exists:
            path.mkdir(parents=True, exist_ok=True)
        return path

    return Path(
        user_data_path(
            appname=APP_NAME,
            appauthor=False,
            roaming=False,
            ensure_exists=ensure_exists,
        )
    )


def database_path(*, ensure_parent: bool = False) -> Path:
    return data_dir(ensure_exists=ensure_parent) / DATABASE_NAME
