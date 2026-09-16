from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from pydantic import BaseModel
from pydantic import Field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user

from app.database.models import AssessmentSession
from app.database.models import LearningProgram
from app.database.models import User

from app.database.session import get_db


router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"],
)


AssessmentStatus = Literal[
    "in_progress",
    "completed",
    "abandoned",
]


class StartAssessmentRequest(BaseModel):
    program_id: int

    max_questions: int = Field(
        default=12,
        ge=5,
        le=30,
    )


class AssessmentResponse(BaseModel):
    id: int
    program_id: int
    program_type: str

    status: AssessmentStatus

    current_question: int
    questions_answered: int
    max_questions: int

    started_at: datetime
    completed_at: datetime | None

    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message: str


def get_owned_program(
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


def get_owned_assessment(
    database: Session,
    user_id: int,
    assessment_id: int,
) -> AssessmentSession:
    statement = (
        select(AssessmentSession)
        .join(
            LearningProgram,
            AssessmentSession.program_id
            == LearningProgram.id,
        )
        .where(
            AssessmentSession.id
            == assessment_id,
            LearningProgram.user_id
            == user_id,
        )
    )

    assessment = database.scalar(
        statement
    )

    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    return assessment


def find_active_assessment(
    database: Session,
    program_id: int,
) -> AssessmentSession | None:
    statement = (
        select(AssessmentSession)
        .where(
            AssessmentSession.program_id
            == program_id,
            AssessmentSession.status
            == "in_progress",
        )
        .order_by(
            AssessmentSession.created_at.desc()
        )
    )

    return database.scalar(
        statement
    )


def serialize_assessment(
    assessment: AssessmentSession,
    program: LearningProgram,
) -> AssessmentResponse:
    return AssessmentResponse(
        id=assessment.id,
        program_id=assessment.program_id,
        program_type=program.program_type,
        status=assessment.status,
        current_question=assessment.current_question,
        questions_answered=assessment.questions_answered,
        max_questions=assessment.max_questions,
        started_at=assessment.started_at,
        completed_at=assessment.completed_at,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
    )


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_assessment(
    request: StartAssessmentRequest,
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    program = get_owned_program(
        database=database,
        user_id=current_user.id,
        program_id=request.program_id,
    )

    if (
        program.starting_strategy
        != "assessment"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This learning program is not "
                "configured to start with an assessment."
            ),
        )

    existing = find_active_assessment(
        database=database,
        program_id=program.id,
    )

    if existing is not None:
        return serialize_assessment(
            assessment=existing,
            program=program,
        )

    assessment = AssessmentSession(
        program_id=program.id,
        status="in_progress",
        current_question=0,
        questions_answered=0,
        max_questions=request.max_questions,
    )

    database.add(assessment)
    database.commit()
    database.refresh(assessment)

    return serialize_assessment(
        assessment=assessment,
        program=program,
    )


@router.get(
    "/program/{program_id}/current",
    response_model=AssessmentResponse | None,
)
async def current_assessment(
    program_id: int,
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    program = get_owned_program(
        database=database,
        user_id=current_user.id,
        program_id=program_id,
    )

    assessment = find_active_assessment(
        database=database,
        program_id=program.id,
    )

    if assessment is None:
        return None

    return serialize_assessment(
        assessment=assessment,
        program=program,
    )


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
)
async def read_assessment(
    assessment_id: int,
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    assessment = get_owned_assessment(
        database=database,
        user_id=current_user.id,
        assessment_id=assessment_id,
    )

    program = assessment.program

    return serialize_assessment(
        assessment=assessment,
        program=program,
    )


@router.post(
    "/{assessment_id}/abandon",
    response_model=MessageResponse,
)
async def abandon_assessment(
    assessment_id: int,
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    assessment = get_owned_assessment(
        database=database,
        user_id=current_user.id,
        assessment_id=assessment_id,
    )

    if assessment.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only an in-progress assessment "
                "can be abandoned."
            ),
        )

    assessment.status = "abandoned"
    assessment.completed_at = datetime.utcnow()

    database.commit()

    return MessageResponse(
        message="Assessment abandoned."
    )
