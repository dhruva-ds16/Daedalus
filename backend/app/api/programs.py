from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from pydantic import BaseModel
from pydantic import Field

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.models import LearningProgram
from app.database.models import User
from app.database.session import get_db


router = APIRouter(
    prefix="/programs",
    tags=["Learning Programs"],
)


ProgramType = Literal[
    "rust",
    "windows",
    "integrated",
]


StartingStrategy = Literal[
    "beginning",
    "assessment",
    "selected_level",
]


ProgramStatus = Literal[
    "setup",
    "active",
    "paused",
    "completed",
]


SelectedLevel = Literal[
    "beginner",
    "intermediate",
    "advanced",
]


DEFAULT_TITLES = {
    "rust": "Rust Programming",
    "windows": "Windows Internals",
    "integrated": "Windows + Rust",
}


class CreateProgramRequest(BaseModel):
    program_type: ProgramType

    title: str | None = Field(
        default=None,
        max_length=150,
    )

    goal: str | None = Field(
        default=None,
        max_length=2000,
    )

    starting_strategy: StartingStrategy = "assessment"

    selected_level: SelectedLevel | None = None


class ProgramResponse(BaseModel):
    id: int
    user_id: int

    program_type: ProgramType

    title: str

    goal: str | None

    starting_strategy: StartingStrategy

    selected_level: SelectedLevel | None

    status: ProgramStatus

    curriculum_version: int

    created_at: datetime
    updated_at: datetime


class UpdateProgramStatusRequest(BaseModel):
    status: ProgramStatus


def serialize_program(
    program: LearningProgram,
) -> ProgramResponse:
    return ProgramResponse(
        id=program.id,
        user_id=program.user_id,
        program_type=program.program_type,
        title=program.title,
        goal=program.goal,
        starting_strategy=program.starting_strategy,
        selected_level=program.selected_level,
        status=program.status,
        curriculum_version=program.curriculum_version,
        created_at=program.created_at,
        updated_at=program.updated_at,
    )


def get_user_program(
    database: Session,
    user_id: int,
    program_id: int,
) -> LearningProgram:
    statement = select(
        LearningProgram
    ).where(
        LearningProgram.id == program_id,
        LearningProgram.user_id == user_id,
    )

    program = database.scalar(
        statement
    )

    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning program not found.",
        )

    return program


@router.get(
    "",
    response_model=list[ProgramResponse],
)
async def list_programs(
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    statement = (
        select(LearningProgram)
        .where(
            LearningProgram.user_id
            == current_user.id
        )
        .order_by(
            LearningProgram.created_at
        )
    )

    programs = database.scalars(
        statement
    ).all()

    return [
        serialize_program(program)
        for program in programs
    ]


@router.post(
    "",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_program(
    request: CreateProgramRequest,
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    if (
        request.starting_strategy
        == "selected_level"
        and request.selected_level is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "selected_level is required when "
                "starting_strategy is selected_level."
            ),
        )

    if (
        request.starting_strategy
        != "selected_level"
    ):
        selected_level = None
    else:
        selected_level = (
            request.selected_level
        )

    title = (
        request.title.strip()
        if request.title
        and request.title.strip()
        else DEFAULT_TITLES[
            request.program_type
        ]
    )

    program = LearningProgram(
        user_id=current_user.id,
        program_type=request.program_type,
        title=title,
        goal=request.goal,
        starting_strategy=(
            request.starting_strategy
        ),
        selected_level=selected_level,
        status="setup",
        curriculum_version=0,
    )

    try:
        database.add(program)
        database.commit()
        database.refresh(program)

    except IntegrityError:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "You already have a learning "
                "program of this type."
            ),
        )

    return serialize_program(
        program
    )


@router.get(
    "/{program_id}",
    response_model=ProgramResponse,
)
async def read_program(
    program_id: int,
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    program = get_user_program(
        database=database,
        user_id=current_user.id,
        program_id=program_id,
    )

    return serialize_program(
        program
    )


@router.patch(
    "/{program_id}/status",
    response_model=ProgramResponse,
)
async def update_program_status(
    program_id: int,
    request: UpdateProgramStatusRequest,
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    program = get_user_program(
        database=database,
        user_id=current_user.id,
        program_id=program_id,
    )

    program.status = request.status

    database.commit()
    database.refresh(program)

    return serialize_program(
        program
    )


@router.delete(
    "/{program_id}",
)
async def delete_program(
    program_id: int,
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    program = get_user_program(
        database=database,
        user_id=current_user.id,
        program_id=program_id,
    )

    title = program.title

    database.delete(program)
    database.commit()

    return {
        "message": (
            f"Learning program "
            f"{title} deleted."
        )
    }
