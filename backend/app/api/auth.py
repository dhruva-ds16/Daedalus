import re

from datetime import datetime

from fastapi import APIRouter
from fastapi import Cookie
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi import status

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from sqlalchemy.orm import Session

from app.config import (
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    SESSION_LIFETIME_DAYS,
)

from app.database.models import User

from app.database.session import get_db

from app.services.auth import (
    InactiveUserError,
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
    authenticate_user,
    create_auth_session,
    create_user,
    delete_auth_session,
    get_auth_session,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


USERNAME_PATTERN = re.compile(
    r"^[a-zA-Z0-9_-]+$"
)


class RegisterRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=30,
    )

    password: str = Field(
        min_length=10,
        max_length=128,
    )

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


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    created_at: datetime


class MessageResponse(BaseModel):
    message: str


def user_response(
    user: User,
) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    database: Session = Depends(get_db),
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

    return user_response(user)


@router.post(
    "/login",
    response_model=UserResponse,
)
async def login(
    request: LoginRequest,
    response: Response,
    database: Session = Depends(get_db),
):
    try:
        user = authenticate_user(
            database=database,
            username=request.username,
            password=request.password,
        )

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    _, raw_token = create_auth_session(
        database=database,
        user=user,
    )

    max_age = (
        SESSION_LIFETIME_DAYS
        * 24
        * 60
        * 60
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=max_age,
        httponly=SESSION_COOKIE_HTTPONLY,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )

    return user_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
)
async def me(
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
    database: Session = Depends(get_db),
):
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    auth_session = get_auth_session(
        database=database,
        raw_token=session_token,
    )

    if auth_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )

    return user_response(
        auth_session.user
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
)
async def logout(
    response: Response,
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
    database: Session = Depends(get_db),
):
    if session_token:
        delete_auth_session(
            database=database,
            raw_token=session_token,
        )

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=SESSION_COOKIE_HTTPONLY,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
    )

    return MessageResponse(
        message="Logged out."
    )