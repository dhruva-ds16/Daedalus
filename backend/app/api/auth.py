import re
from datetime import datetime

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.services.auth import (
    UsernameAlreadyExistsError,
    create_user,
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


class RegisterResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    created_at: datetime


@router.post(
    "/register",
    response_model=RegisterResponse,
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

    return RegisterResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        created_at=user.created_at,
    )
