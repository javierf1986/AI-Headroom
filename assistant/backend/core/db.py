from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.core.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        connect_args: dict = {}
        if settings.database_url.startswith("sqlite"):
            # Allow SQLite to be used across threads (FastAPI runs in a thread pool)
            connect_args = {"check_same_thread": False}
        _engine = create_engine(
            settings.database_url,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def init_db() -> None:
    from backend.core import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
    logger.info("Database initialized (SQLite)")


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
