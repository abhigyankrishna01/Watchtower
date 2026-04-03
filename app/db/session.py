from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def _build_engine():
    if settings.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if ":memory:" in settings.database_url:
            return create_engine(
                settings.database_url,
                connect_args=connect_args,
                poolclass=StaticPool,
                future=True,
            )
        return create_engine(settings.database_url, connect_args=connect_args, future=True)
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


engine = _build_engine()


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
