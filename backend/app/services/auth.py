import hashlib
import secrets

from datetime import datetime
from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import SESSION_LIFETIME_DAYS

from app.database.models import AuthSession
from app.database.models import User

from app.services.security import (
    hash_password,
    password_needs_rehash,
    verify_password,
)


class UsernameAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


def normalize_username(
    username: str,
) -> str:
    return username.strip().lower()


def hash_session_token(
    token: str,
) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


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


def authenticate_user(
    database: Session,
    username: str,
    password: str,
) -> User:
    user = get_user_by_username(
        database=database,
        username=username,
    )

    if user is None:
        raise InvalidCredentialsError(
            "Invalid username or password."
        )

    if not verify_password(
        password=password,
        password_hash=user.password_hash,
    ):
        raise InvalidCredentialsError(
            "Invalid username or password."
        )

    if not user.is_active:
        raise InactiveUserError(
            "User account is inactive."
        )

    if password_needs_rehash(
        user.password_hash
    ):
        user.password_hash = hash_password(
            password
        )

        database.commit()
        database.refresh(user)

    return user


def create_auth_session(
    database: Session,
    user: User,
) -> tuple[AuthSession, str]:
    raw_token = generate_session_token()

    token_hash = hash_session_token(
        raw_token
    )

    now = datetime.utcnow()

    expires_at = now + timedelta(
        days=SESSION_LIFETIME_DAYS
    )

    auth_session = AuthSession(
        user_id=user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=expires_at,
        last_seen_at=now,
    )

    try:
        database.add(auth_session)
        database.commit()
        database.refresh(auth_session)

    except Exception:
        database.rollback()
        raise

    return auth_session, raw_token


def get_auth_session(
    database: Session,
    raw_token: str,
) -> AuthSession | None:
    token_hash = hash_session_token(
        raw_token
    )

    statement = select(AuthSession).where(
        AuthSession.token_hash == token_hash
    )

    auth_session = database.scalar(
        statement
    )

    if auth_session is None:
        return None

    now = datetime.utcnow()

    if auth_session.expires_at <= now:
        database.delete(auth_session)
        database.commit()

        return None

    if not auth_session.user.is_active:
        return None

    auth_session.last_seen_at = now

    database.commit()

    return auth_session


def delete_auth_session(
    database: Session,
    raw_token: str,
) -> None:
    token_hash = hash_session_token(
        raw_token
    )

    statement = delete(
        AuthSession
    ).where(
        AuthSession.token_hash == token_hash
    )

    database.execute(statement)
    database.commit()