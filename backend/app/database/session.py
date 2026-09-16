from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.config import (
    DATABASE_DIR,
    DATABASE_URL,
)


DATABASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[
    Session,
    None,
    None,
]:
    database = SessionLocal()

    try:
        yield database

    finally:
        database.close()