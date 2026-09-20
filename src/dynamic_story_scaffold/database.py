from __future__ import annotations

import platform
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import String, URL, create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .paths import database_path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Installation(Base):
    __tablename__ = "installations"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_version: Mapped[str] = mapped_column(String(64))
    python_version: Mapped[str] = mapped_column(String(64))
    os_name: Mapped[str] = mapped_column(String(64))
    platform: Mapped[str] = mapped_column(String(64))
    database_path: Mapped[str]
    installed_at: Mapped[datetime]


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str]
    updated_at: Mapped[datetime]


class DatabaseNotReady(RuntimeError):
    """Raised when normal runtime code sees missing or stale application state."""


@dataclass(frozen=True)
class DatabaseStatus:
    path: Path
    revision: str | None
    expected_revision: str
    ready: bool
    installation_count: int


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else database_path()
        self.url = URL.create("sqlite+pysqlite", database=str(self.path))
        self._engine: Engine | None = None

    def engine(self) -> Engine:
        if self._engine is None:
            engine = create_engine(self.url)

            @event.listens_for(engine, "connect")
            def _sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            self._engine = engine
        return self._engine

    @contextmanager
    def session(self) -> Iterator[Session]:
        with Session(self.engine()) as session:
            with session.begin():
                yield session

    def _alembic_config(self) -> Config:
        migration_root = resources.files("dynamic_story_scaffold").joinpath("migrations")
        with resources.as_file(migration_root) as script_location:
            config = Config()
            config.set_main_option("script_location", str(script_location))
            return config

    def expected_revision(self) -> str:
        head = ScriptDirectory.from_config(self._alembic_config()).get_current_head()
        if not head:
            raise RuntimeError("DSS migration package has no Alembic head revision")
        return head

    def current_revision(self) -> str | None:
        if not self.path.exists():
            return None
        with self.engine().connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()

    def require_current_schema(self) -> None:
        current = self.current_revision()
        expected = self.expected_revision()
        if current == expected:
            return
        if current is None:
            raise DatabaseNotReady(
                "DSS application state is not initialized. "
                "Run 'dss-maintain setup' after installing or upgrading the package."
            )
        raise DatabaseNotReady(
            f"DSS database schema is {current}, expected {expected}. "
            "Run 'dss-maintain setup' (or 'dss-maintain db migrate' for support work)."
        )

    def upgrade_schema(self) -> None:
        """Installer/support operation: upgrade the application database to head."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        config = self._alembic_config()
        with self.engine().connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    def setup(self, *, package_version: str) -> DatabaseStatus:
        """Installer operation: upgrade schema and record the installed package."""

        self.upgrade_schema()
        with self.session() as session:
            session.add(
                Installation(
                    package_version=package_version,
                    python_version=platform.python_version(),
                    os_name=platform.system(),
                    platform=sys.platform,
                    database_path=str(self.path),
                    installed_at=utc_now(),
                )
            )
        return self.status()

    def status(self) -> DatabaseStatus:
        expected = self.expected_revision()
        revision = self.current_revision()
        if revision is None:
            return DatabaseStatus(
                path=self.path,
                revision=None,
                expected_revision=expected,
                ready=False,
                installation_count=0,
            )

        installation_count = 0
        if self.path.exists():
            try:
                with Session(self.engine()) as session:
                    installation_count = session.scalar(
                        select(func.count()).select_from(Installation)
                    ) or 0
            except Exception:
                # Status is diagnostic and must still report schema mismatch even if
                # an old/broken schema cannot satisfy current ORM queries.
                installation_count = 0

        return DatabaseStatus(
            path=self.path,
            revision=revision,
            expected_revision=expected,
            ready=revision == expected,
            installation_count=int(installation_count),
        )
