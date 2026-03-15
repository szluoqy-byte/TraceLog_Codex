from __future__ import annotations

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine


def _default_db_path() -> str:
    # Default to a repo-local DB file so the prototype runs without extra setup.
    here = Path(__file__).resolve()
    backend_dir = here.parents[1]
    data_dir = backend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "tracelog.db")


def build_engine():
    db_path = os.getenv("TRACELOG_DB_PATH", _default_db_path())
    # Keep check_same_thread=false for FastAPI's default threaded model.
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


engine = build_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session

