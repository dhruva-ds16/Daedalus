from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerifyMismatchError,
)


password_hasher = PasswordHasher()


def hash_password(
    password: str,
) -> str:
    return password_hasher.hash(
        password
    )


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    try:
        return password_hasher.verify(
            password_hash,
            password,
        )

    except (
        VerifyMismatchError,
        InvalidHashError,
    ):
        return False


def password_needs_rehash(
    password_hash: str,
) -> bool:
    try:
        return password_hasher.check_needs_rehash(
            password_hash
        )

    except InvalidHashError:
        return True
