from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .builds import BuildManager
from .database import Database
from .platform import current_platform
from .version import package_version


def _status_payload(database: Database) -> dict[str, object]:
    status = database.status()
    platform_info = current_platform()
    return {
        "os_name": platform_info.os_name,
        "sys_platform": platform_info.sys_platform,
        "data_directory": str(platform_info.data_directory),
        "database_path": str(status.path),
        "schema_version": status.schema_version,
        "installation_count": status.installation_count,
        "build_count": status.build_count,
    }


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dss",
        description="Dynamic Story Scaffold build and runtime management.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="Override the application SQLite database path.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser(
        "install",
        help="Create or migrate the per-user application database.",
    )
    install.add_argument("--json", action="store_true")

    paths = subparsers.add_parser(
        "paths",
        help="Show resolved application paths.",
    )
    paths.add_argument("--json", action="store_true")

    database = subparsers.add_parser("db", help="Database operations.")
    db_subparsers = database.add_subparsers(dest="db_command", required=True)
    db_status = db_subparsers.add_parser("status", help="Show database status.")
    db_status.add_argument("--json", action="store_true")
    db_migrate = db_subparsers.add_parser(
        "migrate",
        help="Apply pending database migrations.",
    )
    db_migrate.add_argument("--json", action="store_true")

    build = subparsers.add_parser(
        "build",
        help="Build wheel/sdist and record the build in SQLite.",
    )
    build.add_argument("--project-root", type=Path, default=Path("."))
    build.add_argument("--output-dir", type=Path, default=Path("dist"))
    build.add_argument("--clean", action="store_true")
    build.add_argument("--json", action="store_true")

    builds = subparsers.add_parser("builds", help="Query recorded builds.")
    builds_subparsers = builds.add_subparsers(
        dest="builds_command",
        required=True,
    )
    builds_list = builds_subparsers.add_parser("list", help="List recent builds.")
    builds_list.add_argument("--limit", type=int, default=20)
    builds_list.add_argument("--json", action="store_true")

    return parser


def _database_from_args(args: argparse.Namespace) -> Database:
    return Database(args.database) if args.database else Database()


def main(argv: Sequence[str] | None = None) -> int:
    parser = _make_parser()
    args = parser.parse_args(argv)
    database = _database_from_args(args)

    if args.command == "install":
        status = database.install(package_version=package_version())
        payload = {
            "installed": True,
            "package_version": package_version(),
            **_status_payload(database),
        }
        _print_payload(payload, as_json=args.json)
        return 0

    if args.command == "paths":
        platform_info = current_platform()
        payload = {
            "os_name": platform_info.os_name,
            "sys_platform": platform_info.sys_platform,
            "data_directory": str(platform_info.data_directory),
            "database_path": str(
                args.database if args.database else platform_info.database
            ),
        }
        _print_payload(payload, as_json=args.json)
        return 0

    if args.command == "db":
        if args.db_command == "migrate":
            database.ensure_schema()
        _print_payload(_status_payload(database), as_json=args.json)
        return 0

    if args.command == "build":
        record = BuildManager(database).build(
            project_root=args.project_root,
            output_dir=args.output_dir,
            clean=args.clean,
        )
        payload = {
            "id": record.id,
            "status": record.status,
            "package_version": record.package_version,
            "git_commit": record.git_commit,
            "git_branch": record.git_branch,
            "output_dir": str(record.output_dir),
            "artifacts": [
                {
                    "path": str(artifact.path),
                    "kind": artifact.kind,
                    "size_bytes": artifact.size_bytes,
                    "sha256": artifact.sha256,
                }
                for artifact in record.artifacts
            ],
        }
        _print_payload(payload, as_json=args.json)
        return 0

    if args.command == "builds" and args.builds_command == "list":
        records = BuildManager(database).list_builds(limit=args.limit)
        payload = [
            {
                "id": record.id,
                "status": record.status,
                "package_version": record.package_version,
                "git_commit": record.git_commit,
                "git_branch": record.git_branch,
                "output_dir": str(record.output_dir),
                "artifact_count": len(record.artifacts),
                "error": record.error,
            }
            for record in records
        ]
        _print_payload(payload, as_json=args.json)
        return 0

    parser.error("unsupported command")
    return 2


def installer_main(argv: Sequence[str] | None = None) -> int:
    forwarded = list(sys.argv[1:] if argv is None else argv)
    return main(["install", *forwarded])


def _print_payload(payload: object, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
        return

    if isinstance(payload, list):
        for item in payload:
            print(item)
        return

    print(payload)
