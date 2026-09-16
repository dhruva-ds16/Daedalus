from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.models import LearnerProfile, User
from app.database.session import get_db


router = APIRouter(
    prefix="/profile",
    tags=["Learner Profile"],
)


ProgrammingExperience = Literal[
    "unknown",
    "beginner",
    "intermediate",
    "advanced",
]

PreferredDepth = Literal[
    "concise",
    "balanced",
    "detailed",
]

StudyIntensity = Literal[
    "casual",
    "standard",
    "intensive",
]


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    display_name: str | None
    programming_experience: ProgrammingExperience
    preferred_depth: PreferredDepth
    study_intensity: StudyIntensity
    learning_goal: str | None
    onboarding_complete: bool
    created_at: datetime
    updated_at: datetime


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(
        default=None,
        max_length=100,
    )

    programming_experience: ProgrammingExperience = "unknown"
    preferred_depth: PreferredDepth = "balanced"
    study_intensity: StudyIntensity = "standard"

    learning_goal: str | None = Field(
        default=None,
        max_length=2000,
    )


def get_profile(
    database: Session,
    user_id: int,
) -> LearnerProfile | None:
    statement = select(
        LearnerProfile
    ).where(
        LearnerProfile.user_id == user_id
    )

    return database.scalar(
        statement
    )


def get_or_create_profile(
    database: Session,
    user: User,
) -> LearnerProfile:
    profile = get_profile(
        database=database,
        user_id=user.id,
    )

    if profile is not None:
        return profile

    profile = LearnerProfile(
        user_id=user.id,
        display_name=user.username,
    )

    database.add(profile)
    database.commit()
    database.refresh(profile)

    return profile


def serialize_profile(
    profile: LearnerProfile,
) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        programming_experience=(
            profile.programming_experience
        ),
        preferred_depth=(
            profile.preferred_depth
        ),
        study_intensity=(
            profile.study_intensity
        ),
        learning_goal=profile.learning_goal,
        onboarding_complete=(
            profile.onboarding_complete
        ),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get(
    "",
    response_model=ProfileResponse,
)
async def read_profile(
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    profile = get_or_create_profile(
        database=database,
        user=current_user,
    )

    return serialize_profile(
        profile
    )


@router.put(
    "",
    response_model=ProfileResponse,
)
async def update_profile(
    request: UpdateProfileRequest,
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    profile = get_or_create_profile(
        database=database,
        user=current_user,
    )

    profile.display_name = (
        request.display_name
    )

    profile.programming_experience = (
        request.programming_experience
    )

    profile.preferred_depth = (
        request.preferred_depth
    )

    profile.study_intensity = (
        request.study_intensity
    )

    profile.learning_goal = (
        request.learning_goal
    )

    profile.onboarding_complete = True

    database.commit()
    database.refresh(profile)

    return serialize_profile(
        profile
    )