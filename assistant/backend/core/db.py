from __future__ import annotations

import logging
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
        connect_args: dict[str, int] = {}
        if settings.database_url.startswith("postgresql"):
            connect_args = {"connect_timeout": 2}
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def init_db() -> bool:
    try:
        from backend.core import models  # noqa: F401

        engine = get_engine()
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
        return True
    except Exception as exc:
        logger.warning("Database unavailable, falling back to in-memory preferences: %s", exc)
        return False


@contextmanager
def session_scope() -> Session:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
