from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import (
    DATABASE_URL,
    SQLITE_MAX_OVERFLOW,
    SQLITE_POOL_SIZE,
    SQLITE_POOL_TIMEOUT,
)

connect_args: dict[str, Any] = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = SQLITE_POOL_TIMEOUT

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=SQLITE_POOL_SIZE,
    max_overflow=SQLITE_MAX_OVERFLOW,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
