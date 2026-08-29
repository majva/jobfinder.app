from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.infrastructure.context.sql_db.sqlite_dbcontext import Base
import src.infrastructure.models.candidate  # noqa: F401
import src.infrastructure.models.job  # noqa: F401
import src.infrastructure.models.job_match  # noqa: F401
import src.infrastructure.models.search_run  # noqa: F401

target_metadata = Base.metadata


def _normalize_database_url(url: str) -> str:
    return url.replace("sqlite+aiosqlite://", "sqlite://")


def _resolve_sqlite_url(url: str) -> str:
    url = _normalize_database_url(url)
    prefix = "sqlite:///"
    if url.startswith(prefix):
        raw_path = url[len(prefix):]
        path = Path(raw_path)
        if not path.is_absolute():
            project_root = Path(__file__).resolve().parents[3]
            path = (project_root / path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"
    return url


def get_database_url() -> str:
    url = os.environ.get("SQLITE_CONNECTION_STRING") or os.environ.get("DATABASE_URL")
    if url:
        return _resolve_sqlite_url(url)

    url = config.get_main_option("sqlalchemy.url")
    if url:
        return _resolve_sqlite_url(url)

    raise RuntimeError("Database URL is not configured.")


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
