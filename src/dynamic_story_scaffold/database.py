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
from sqlalchemy import ForeignKey, String, URL, create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

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


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_version: Mapped[str] = mapped_column(String(64))
    git_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    git_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_root: Mapped[str]
    output_dir: Mapped[str]
    created_at: Mapped[datetime]
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="build",
        cascade="all, delete-orphan",
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_id: Mapped[int] = mapped_column(
        ForeignKey("builds.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32))
    path: Mapped[str]
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    build: Mapped[Build] = relationship(back_populates="artifacts")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str]
    updated_at: Mapped[datetime]


@dataclass(frozen=True)
class DatabaseStatus:
    path: Path
    revision: str | None
    installation_count: int
    build_count: int


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

    def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        migration_root = resources.files("dynamic_story_scaffold").joinpath("migrations")
        with resources.as_file(migration_root) as script_location:
            config = Config()
            config.set_main_option("script_location", str(script_location))
            with self.engine().begin() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")

    def install(self, *, package_version: str) -> DatabaseStatus:
        self.migrate()
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
        if not self.path.exists():
            return DatabaseStatus(self.path, None, 0, 0)

        engine = self.engine()
        with engine.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()

        if revision is None:
            return DatabaseStatus(self.path, None, 0, 0)

        with Session(engine) as session:
            installation_count = session.scalar(
                select(func.count()).select_from(Installation)
            ) or 0
            build_count = session.scalar(select(func.count()).select_from(Build)) or 0

        return DatabaseStatus(
            path=self.path,
            revision=revision,
            installation_count=int(installation_count),
            build_count=int(build_count),
        )
