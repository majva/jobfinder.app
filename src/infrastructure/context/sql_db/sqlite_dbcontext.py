from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

from src.infrastructure.di.inject import inject
from src.infrastructure.utils.config_reader import ConfigReader

Base = declarative_base()


def _ensure_job_applied_column(connection) -> None:
    rows = connection.exec_driver_sql("PRAGMA table_info(job)").fetchall()
    names = {row[1] for row in rows}
    if "applied" not in names:
        connection.exec_driver_sql(
            "ALTER TABLE job ADD COLUMN applied BOOLEAN NOT NULL DEFAULT 0"
        )


def _resolve_sqlite_url(url: str, project_root: Path) -> str:
    prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
    for prefix in prefixes:
        if url.startswith(prefix):
            raw_path = url[len(prefix):]
            path = Path(raw_path)
            if not path.is_absolute():
                path = (project_root / path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            driver = "sqlite+aiosqlite" if "aiosqlite" in prefix else "sqlite"
            return f"{driver}:///{path}"
    return url


@inject
class SqliteDbContext:
    __di_singleton__ = True

    def __init__(self, config_reader: ConfigReader):
        url = config_reader.get("database.url")
        if not url:
            raise RuntimeError("database.url is required in appsettings.")

        project_root = config_reader.get_project_root()
        async_url = _resolve_sqlite_url(str(url), project_root)

        engine_kwargs = {"echo": False}
        if async_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = StaticPool

        self._engine = create_async_engine(async_url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self):
        async with self._session_factory() as session:
            yield session

    async def ensure_schema(self) -> None:
        import src.infrastructure.models.candidate  # noqa: F401
        import src.infrastructure.models.job  # noqa: F401
        import src.infrastructure.models.job_match  # noqa: F401
        import src.infrastructure.models.search_run  # noqa: F401

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_ensure_job_applied_column)
