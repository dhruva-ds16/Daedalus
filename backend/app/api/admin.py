import re

from datetime import datetime

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_admin,
)

from app.database.models import (
    AuthSession,
    User,
)

from app.database.session import get_db

from app.services.auth import (
    UsernameAlreadyExistsError,
    create_user,
)

from app.services.security import (
    hash_password,
)


router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
)


USERNAME_PATTERN = re.compile(
    r"^[a-zA-Z0-9_-]+$"
)


# ---------------------------------------------------------
# Request / response models
# ---------------------------------------------------------

class AdminUserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime


class AdminCreateUserRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=30,
    )

    password: str = Field(
        min_length=10,
        max_length=128,
    )

    is_admin: bool = False

    @field_validator("username")
    @classmethod
    def validate_username(
        cls,
        username: str,
    ) -> str:
        username = username.strip()

        if not USERNAME_PATTERN.fullmatch(
            username
        ):
            raise ValueError(
                "Username may contain only "
                "letters, numbers, underscores, "
                "and hyphens."
            )

        return username

    @field_validator("password")
    @classmethod
    def validate_password(
        cls,
        password: str,
    ) -> str:
        return validate_password_value(
            password
        )


class ResetPasswordRequest(BaseModel):
    password: str = Field(
        min_length=10,
        max_length=128,
    )

    @field_validator("password")
    @classmethod
    def validate_password(
        cls,
        password: str,
    ) -> str:
        return validate_password_value(
            password
        )


class SetActiveRequest(BaseModel):
    is_active: bool


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def validate_password_value(
    password: str,
) -> str:
    if password != password.strip():
        raise ValueError(
            "Password cannot begin or end "
            "with whitespace."
        )

    if not any(
        character.isalpha()
        for character in password
    ):
        raise ValueError(
            "Password must contain at least "
            "one letter."
        )

    if not any(
        character.isdigit()
        for character in password
    ):
        raise ValueError(
            "Password must contain at least "
            "one number."
        )

    return password


def serialize_user(
    user: User,
) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


def get_target_user(
    database: Session,
    user_id: int,
) -> User:
    user = database.get(
        User,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


def invalidate_user_sessions(
    database: Session,
    user_id: int,
) -> None:
    database.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user_id
        )
    )


def count_active_admins(
    database: Session,
) -> int:
    statement = select(
        func.count(User.id)
    ).where(
        User.is_admin.is_(True),
        User.is_active.is_(True),
    )

    return (
        database.scalar(statement)
        or 0
    )


# ---------------------------------------------------------
# List users
# ---------------------------------------------------------

@router.get(
    "/users",
    response_model=list[
        AdminUserResponse
    ],
)
async def list_users(
    database: Session = Depends(
        get_db
    ),
    current_admin: User = Depends(
        get_current_admin
    ),
):
    statement = (
        select(User)
        .order_by(
            User.username
        )
    )

    users = database.scalars(
        statement
    ).all()

    return [
        serialize_user(user)
        for user in users
    ]


# ---------------------------------------------------------
# Create user
# ---------------------------------------------------------

@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_user(
    request: AdminCreateUserRequest,
    database: Session = Depends(
        get_db
    ),
    current_admin: User = Depends(
        get_current_admin
    ),
):
    try:
        user = create_user(
            database=database,
            username=request.username,
            password=request.password,
        )

    except UsernameAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        )

    if request.is_admin:
        user.is_admin = True

        database.commit()
        database.refresh(user)

    return serialize_user(user)


# ---------------------------------------------------------
# Reset password
# ---------------------------------------------------------

@router.post(
    "/users/{user_id}/reset-password",
    response_model=MessageResponse,
)
async def reset_user_password(
    user_id: int,
    request: ResetPasswordRequest,
    database: Session = Depends(
        get_db
    ),
    current_admin: User = Depends(
        get_current_admin
    ),
):
    user = get_target_user(
        database,
        user_id,
    )

    user.password_hash = (
        hash_password(
            request.password
        )
    )

    invalidate_user_sessions(
        database,
        user.id,
    )

    database.commit()

    return MessageResponse(
        message=(
            f"Password reset for "
            f"{user.username}. "
            "Existing sessions were revoked."
        )
    )


# ---------------------------------------------------------
# Enable / disable user
# ---------------------------------------------------------

@router.patch(
    "/users/{user_id}/active",
    response_model=AdminUserResponse,
)
async def set_user_active(
    user_id: int,
    request: SetActiveRequest,
    database: Session = Depends(
        get_db
    ),
    current_admin: User = Depends(
        get_current_admin
    ),
):
    user = get_target_user(
        database,
        user_id,
    )

    if (
        user.id == current_admin.id
        and not request.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "You cannot deactivate "
                "your own account."
            ),
        )

    if (
        user.is_admin
        and user.is_active
        and not request.is_active
        and count_active_admins(
            database
        ) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The last active administrator "
                "cannot be deactivated."
            ),
        )

    user.is_active = (
        request.is_active
    )

    if not user.is_active:
        invalidate_user_sessions(
            database,
            user.id,
        )

    database.commit()
    database.refresh(user)

    return serialize_user(user)


# ---------------------------------------------------------
# Delete user
# ---------------------------------------------------------

@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
)
async def delete_user(
    user_id: int,
    database: Session = Depends(
        get_db
    ),
    current_admin: User = Depends(
        get_current_admin
    ),
):
    user = get_target_user(
        database,
        user_id,
    )

    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "You cannot delete "
                "your own account."
            ),
        )

    if (
        user.is_admin
        and user.is_active
        and count_active_admins(
            database
        ) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The last active administrator "
                "cannot be deleted."
            ),
        )

    username = user.username

    invalidate_user_sessions(
        database,
        user.id,
    )

    database.delete(user)
    database.commit()

    return MessageResponse(
        message=(
            f"User {username} deleted."
        )
    )
