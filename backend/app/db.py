"""Database engine, session management and the settings key-value store."""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from . import config


class Base(DeclarativeBase):
    pass


engine = create_engine(
    config.DB_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """For jobs / scripts outside request context."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)
    # WAL improves concurrent read behaviour (scheduler thread + API thread).
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.commit()
    _ensure_default_settings()


# ---------------------------------------------------------------- settings --

def _ensure_default_settings() -> None:
    from .models import Setting

    with session_scope() as db:
        existing = {s.key for s in db.query(Setting).all()}
        for key, value in config.DEFAULT_SETTINGS.items():
            if key not in existing:
                db.add(Setting(key=key, value=json.dumps(value)))


def get_setting(db: Session, key: str, default: Any = None) -> Any:
    from .models import Setting

    row = db.get(Setting, key)
    if row is None:
        return config.DEFAULT_SETTINGS.get(key, default)
    try:
        return json.loads(row.value)
    except (TypeError, json.JSONDecodeError):
        return row.value


def set_setting(db: Session, key: str, value: Any) -> None:
    from .models import Setting

    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=json.dumps(value)))
    else:
        row.value = json.dumps(value)


def all_settings(db: Session) -> dict[str, Any]:
    from .models import Setting

    out: dict[str, Any] = dict(config.DEFAULT_SETTINGS)
    for row in db.query(Setting).all():
        try:
            out[row.key] = json.loads(row.value)
        except (TypeError, json.JSONDecodeError):
            out[row.key] = row.value
    return out
