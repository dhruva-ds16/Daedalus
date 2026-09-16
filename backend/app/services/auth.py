from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import User
from app.services.security import hash_password


class UsernameAlreadyExistsError(Exception):
    pass


def normalize_username(
    username: str,
) -> str:
    return username.strip().lower()


def get_user_by_username(
    database: Session,
    username: str,
) -> User | None:
    normalized_username = normalize_username(
        username
    )

    statement = select(User).where(
        User.username == normalized_username
    )

    return database.scalar(statement)


def create_user(
    database: Session,
    username: str,
    password: str,
) -> User:
    normalized_username = normalize_username(
        username
    )

    existing_user = get_user_by_username(
        database=database,
        username=normalized_username,
    )

    if existing_user is not None:
        raise UsernameAlreadyExistsError(
            "Username already exists."
        )

    user = User(
        username=normalized_username,
        password_hash=hash_password(
            password
        ),
    )

    try:
        database.add(user)
        database.commit()
        database.refresh(user)

    except Exception:
        database.rollback()
        raise

    return user
