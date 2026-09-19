from __future__ import annotations

import platform as _platform
import sys
from dataclasses import dataclass
from pathlib import Path

from .paths import data_dir, database_path


@dataclass(frozen=True)
class PlatformInfo:
    os_name: str
    sys_platform: str
    data_directory: Path
    database: Path


def current_platform(*, ensure_data_dir: bool = False) -> PlatformInfo:
    directory = data_dir(ensure_exists=ensure_data_dir)
    return PlatformInfo(
        os_name=_platform.system(),
        sys_platform=sys.platform,
        data_directory=directory,
        database=database_path(ensure_parent=ensure_data_dir),
    )
