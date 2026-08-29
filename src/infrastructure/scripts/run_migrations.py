"""
Alembic migration runner.

Usage:
    python src/infrastructure/scripts/run_migrations.py --upgrade
    python src/infrastructure/scripts/run_migrations.py --autogenerate -m "describe change"
    python src/infrastructure/scripts/run_migrations.py --sync -m "describe change"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _normalize_database_url(url: str) -> str:
    return url.replace("sqlite+aiosqlite://", "sqlite://")


def _resolve_sqlite_url(url: str) -> str:
    url = _normalize_database_url(url)
    prefix = "sqlite:///"
    if url.startswith(prefix):
        raw_path = url[len(prefix):]
        path = Path(raw_path)
        if not path.is_absolute():
            path = (_project_root() / path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"
    return url


def _resolve_database_url() -> str:
    url = os.environ.get("SQLITE_CONNECTION_STRING") or os.environ.get("DATABASE_URL")
    if url:
        return _resolve_sqlite_url(url)

    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.infrastructure.utils.config_reader import ConfigReader

    config_reader = ConfigReader()
    url = config_reader.get("database.url")
    if url:
        return _resolve_sqlite_url(str(url))

    raise RuntimeError("database.url is not set in appsettings.")


def get_alembic_config() -> Config:
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    alembic_ini = root / "src" / "infrastructure" / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(root / "src" / "infrastructure" / "alembic"))
    config.set_main_option("sqlalchemy.url", _resolve_database_url())
    return config


def upgrade(revision: str = "head") -> None:
    print(f"[migrate] Applying migrations up to: {revision}")
    command.upgrade(get_alembic_config(), revision)
    print("[migrate] Database is up to date.")


def autogenerate(message: str) -> None:
    if not message:
        raise ValueError("A migration message is required for --autogenerate.")

    print(f"[migrate] Generating migration: {message}")
    command.revision(get_alembic_config(), message=message, autogenerate=True)
    print("[migrate] Migration file created.")


def sync(message: str, revision: str = "head") -> None:
    autogenerate(message)
    upgrade(revision)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Alembic database migrations.")
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--autogenerate", action="store_true")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("-m", "--message", default="")
    parser.add_argument("--revision", default="head")
    args = parser.parse_args()

    if args.sync:
        sync(args.message, args.revision)
        return
    if args.autogenerate:
        autogenerate(args.message)
        return
    upgrade(args.revision)


if __name__ == "__main__":
    main()
