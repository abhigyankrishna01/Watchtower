from __future__ import annotations

import os
import sys
from logging.config import fileConfig

# Add the project root to sys.path so app.* imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

# Load .env from the project root before reading any env vars
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_database_url() -> str:
    """
    Resolve the database URL with strict precedence:
      1. DATABASE_URL environment variable (set in .env or shell)
      2. settings.database_url from app.core.config

    Heroku/Supabase fix: replace the legacy postgres:// scheme with postgresql://
    so SQLAlchemy 1.4+ doesn't reject it.

    Exits immediately with a clear error if no URL is found — no silent fallback
    to the SQLite URL baked into alembic.ini.
    """
    url = os.getenv("DATABASE_URL") or getattr(settings, "database_url", None)

    if not url:
        print("CRITICAL ERROR: DATABASE_URL NOT FOUND")  # noqa: T201
        sys.exit(1)

    # Fix the legacy postgres:// scheme (Heroku, Supabase, Render, Railway, etc.)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


def run_migrations_offline() -> None:
    """Generate SQL without a live connection (alembic upgrade --sql)."""
    url = _get_database_url()
    # Override the ini value so the offline SQL output targets the right dialect
    config.set_main_option("sqlalchemy.url", url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    url = _get_database_url()

    # Hard-create the engine from the resolved URL.
    # We deliberately avoid engine_from_config / config.get_section() so the
    # SQLite URL in alembic.ini can never bleed through.
    engine = create_engine(url, poolclass=pool.NullPool)

    with engine.connect() as connection:
        # Smoke-test: confirm we're NOT on SQLite
        dialect = connection.dialect.name
        if dialect == "sqlite":
            print(  # noqa: T201
                f"CRITICAL ERROR: Connected to SQLite despite DATABASE_URL={url!r}. "
                "This should never happen — check your .env loading."
            )
            sys.exit(1)

        print(f"[alembic] dialect={dialect}  url={url[:60]}...")  # noqa: T201

        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
