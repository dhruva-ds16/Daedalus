import json

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

from app.database.models import AssessmentQuestion
from app.database.models import AssessmentSession
from app.database.models import LearnerProfile
from app.database.models import LearningProgram
from app.database.models import User

from app.database.session import get_db

from app.services.assessment_evaluator import (
    EvaluationError,
    classification_from_score,
    evaluate_assessment_answer,
)

from app.services.assessment_planner import (
    AssessmentPlanningError,
    plan_assessment_question,
)

from app.services.assessment_validator import (
    AssessmentValidationError,
    validate_assessment_question,
)


router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"],
)


AssessmentStatus = Literal[
    "in_progress",
    "completed",
    "abandoned",
]


Difficulty = Literal[
    "beginner",
    "intermediate",
    "advanced",
]


MAX_PLANNING_ATTEMPTS = 3


class StartAssessmentRequest(BaseModel):
    program_id: int

    max_questions: int = Field(
        default=12,
        ge=5,
        le=30,
    )


class PlanQuestionRequest(BaseModel):
    model: str = Field(
        min_length=1,
        max_length=200,
    )


class SubmitAnswerRequest(BaseModel):
    model: str = Field(
        min_length=1,
        max_length=200,
    )

    answer: str = Field(
        min_length=1,
        max_length=10000,
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


class QuestionResponse(BaseModel):
    id: int
    assessment_id: int
    sequence_number: int
    concept: str
    difficulty: Difficulty
    question_text: str
    answered: bool
    created_at: datetime


class AnswerEvaluationResponse(BaseModel):
    question_id: int
    concept: str
    difficulty: Difficulty
    score: float
    classification: str
    demonstrated: list[str]
    gaps: list[str]
    feedback: str
    questions_answered: int
    max_questions: int
    assessment_complete: bool


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
            AssessmentSession.id == assessment_id,
            LearningProgram.user_id == user_id,
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


def get_owned_question(
    database: Session,
    user_id: int,
    assessment_id: int,
    question_id: int,
) -> AssessmentQuestion:
    statement = (
        select(AssessmentQuestion)
        .join(
            AssessmentSession,
            AssessmentQuestion.assessment_id
            == AssessmentSession.id,
        )
        .join(
            LearningProgram,
            AssessmentSession.program_id
            == LearningProgram.id,
        )
        .where(
            AssessmentQuestion.id == question_id,
            AssessmentQuestion.assessment_id == assessment_id,
            LearningProgram.user_id == user_id,
        )
    )

    question = database.scalar(
        statement
    )

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment question not found.",
        )

    return question


def get_learner_profile(
    database: Session,
    user: User,
) -> LearnerProfile:
    statement = select(
        LearnerProfile
    ).where(
        LearnerProfile.user_id == user.id
    )

    profile = database.scalar(
        statement
    )

    if profile is not None:
        return profile

    profile = LearnerProfile(
        user_id=user.id,
        display_name=user.username,
    )

    database.add(profile)

    try:
        database.commit()
        database.refresh(profile)

        return profile

    except IntegrityError:
        database.rollback()

        profile = database.scalar(
            statement
        )

        if profile is None:
            raise

        return profile


def find_active_assessment(
    database: Session,
    program_id: int,
) -> AssessmentSession | None:
    statement = (
        select(AssessmentSession)
        .where(
            AssessmentSession.program_id == program_id,
            AssessmentSession.status == "in_progress",
        )
        .order_by(
            AssessmentSession.created_at.desc()
        )
    )

    return database.scalar(
        statement
    )


def find_unanswered_question(
    database: Session,
    assessment_id: int,
) -> AssessmentQuestion | None:
    statement = (
        select(AssessmentQuestion)
        .where(
            AssessmentQuestion.assessment_id
            == assessment_id,

            AssessmentQuestion.learner_answer
            .is_(None),
        )
        .order_by(
            AssessmentQuestion.sequence_number
        )
    )

    return database.scalar(
        statement
    )


def find_question_by_sequence(
    database: Session,
    assessment_id: int,
    sequence_number: int,
) -> AssessmentQuestion | None:
    statement = (
        select(AssessmentQuestion)
        .where(
            AssessmentQuestion.assessment_id
            == assessment_id,

            AssessmentQuestion.sequence_number
            == sequence_number,
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


def serialize_question(
    question: AssessmentQuestion,
) -> QuestionResponse:
    return QuestionResponse(
        id=question.id,
        assessment_id=question.assessment_id,
        sequence_number=question.sequence_number,
        concept=question.concept,
        difficulty=question.difficulty,
        question_text=question.question_text,
        answered=(
            question.learner_answer is not None
        ),
        created_at=question.created_at,
    )


def build_previous_evidence(
    assessment: AssessmentSession,
) -> list[dict]:
    evidence_items = []

    for question in assessment.questions:
        if question.learner_answer is None:
            continue

        stored_evidence = {}

        if question.evidence:
            try:
                parsed = json.loads(
                    question.evidence
                )

                if isinstance(
                    parsed,
                    dict,
                ):
                    stored_evidence = parsed

            except json.JSONDecodeError:
                stored_evidence = {}

        evidence_items.append(
            {
                "question_number":
                    question.sequence_number,

                "concept":
                    question.concept,

                "difficulty":
                    question.difficulty,

                "score":
                    question.score,

                "classification":
                    stored_evidence.get(
                        "classification"
                    ),

                "demonstrated":
                    stored_evidence.get(
                        "demonstrated",
                        [],
                    ),

                "gaps":
                    stored_evidence.get(
                        "gaps",
                        [],
                    ),

                "reasoning_summary":
                    stored_evidence.get(
                        "reasoning_summary"
                    ),
            }
        )

    return evidence_items


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

    try:
        database.commit()
        database.refresh(assessment)

    except IntegrityError:
        database.rollback()

        existing = find_active_assessment(
            database=database,
            program_id=program.id,
        )

        if existing is None:
            raise

        return serialize_assessment(
            assessment=existing,
            program=program,
        )

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

    return serialize_assessment(
        assessment=assessment,
        program=assessment.program,
    )


@router.post(
    "/{assessment_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def plan_next_question(
    assessment_id: int,
    request: PlanQuestionRequest,
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
            detail="Assessment is not in progress.",
        )

    existing = find_unanswered_question(
        database=database,
        assessment_id=assessment.id,
    )

    if existing is not None:
        return serialize_question(
            existing
        )

    if (
        assessment.questions_answered
        >= assessment.max_questions
    ):
        assessment.status = "completed"
        assessment.completed_at = datetime.utcnow()

        database.commit()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment is complete.",
        )

    profile = get_learner_profile(
        database=database,
        user=current_user,
    )

    previous_evidence = (
        build_previous_evidence(
            assessment
        )
    )

    question_number = (
        assessment.questions_answered
        + 1
    )

    rejected_candidates = []

    accepted_plan = None
    accepted_validation = None

    for attempt in range(
        1,
        MAX_PLANNING_ATTEMPTS + 1,
    ):
        existing = find_unanswered_question(
            database=database,
            assessment_id=assessment.id,
        )

        if existing is not None:
            return serialize_question(
                existing
            )

        try:
            planned = (
                await plan_assessment_question(
                    model=request.model,

                    program_type=(
                        assessment
                        .program
                        .program_type
                    ),

                    program_goal=(
                        assessment
                        .program
                        .goal
                    ),

                    learner_experience=(
                        profile
                        .programming_experience
                    ),

                    learner_goal=(
                        profile
                        .learning_goal
                    ),

                    preferred_depth=(
                        profile
                        .preferred_depth
                    ),

                    question_number=(
                        question_number
                    ),

                    max_questions=(
                        assessment
                        .max_questions
                    ),

                    previous_evidence=(
                        previous_evidence
                    ),

                    rejected_candidates=(
                        rejected_candidates
                    ),
                )
            )

        except AssessmentPlanningError as exc:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_503_SERVICE_UNAVAILABLE
                ),
                detail=str(exc),
            )

        try:
            validation = (
                await validate_assessment_question(
                    model=request.model,

                    program_type=(
                        assessment
                        .program
                        .program_type
                    ),

                    concept=(
                        planned.concept
                    ),

                    difficulty=(
                        planned.difficulty
                    ),

                    question_text=(
                        planned.question_text
                    ),

                    expected_topics=(
                        planned.expected_topics
                    ),

                    evaluator_notes=(
                        planned.evaluator_notes
                    ),
                )
            )

        except AssessmentValidationError as exc:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_503_SERVICE_UNAVAILABLE
                ),
                detail=str(exc),
            )

        if validation.approved:
            accepted_plan = planned
            accepted_validation = validation
            break

        rejected_candidates.append(
            {
                "attempt": attempt,

                "concept":
                    planned.concept,

                "difficulty":
                    planned.difficulty,

                "question_text":
                    planned.question_text,

                "issues":
                    validation.issues,

                "rejection_reason":
                    validation.rejection_reason,
            }
        )

    if (
        accepted_plan is None
        or accepted_validation is None
    ):
        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Daedalus could not produce "
                "a sufficiently reliable assessment "
                "question after multiple attempts."
            ),
        )

    existing = find_unanswered_question(
        database=database,
        assessment_id=assessment.id,
    )

    if existing is not None:
        return serialize_question(
            existing
        )

    existing_sequence = (
        find_question_by_sequence(
            database=database,
            assessment_id=assessment.id,
            sequence_number=question_number,
        )
    )

    if existing_sequence is not None:
        return serialize_question(
            existing_sequence
        )

    validation_metadata = {
        "approved":
            accepted_validation.approved,

        "factual_score":
            accepted_validation.factual_score,

        "clarity_score":
            accepted_validation.clarity_score,

        "rubric_score":
            accepted_validation.rubric_score,

        "difficulty_score":
            accepted_validation.difficulty_score,

        "issues":
            accepted_validation.issues,
    }

    planner_metadata = {
        "selection_reason":
            accepted_plan.selection_reason,

        "validation":
            validation_metadata,

        "rejected_candidates":
            rejected_candidates,
    }

    question = AssessmentQuestion(
        assessment_id=assessment.id,

        sequence_number=(
            question_number
        ),

        concept=(
            accepted_plan.concept
        ),

        difficulty=(
            accepted_plan.difficulty
        ),

        question_text=(
            accepted_plan.question_text
        ),

        expected_topics=json.dumps(
            accepted_plan.expected_topics
        ),

        evaluator_notes=(
            accepted_plan.evaluator_notes
        ),

        evidence=json.dumps(
            {
                "planner":
                    planner_metadata
            }
        ),
    )

    database.add(question)

    assessment.current_question = (
        question_number
    )

    try:
        database.commit()
        database.refresh(question)

    except IntegrityError:
        database.rollback()

        existing = (
            find_question_by_sequence(
                database=database,
                assessment_id=assessment.id,
                sequence_number=question_number,
            )
        )

        if existing is None:
            existing = (
                find_unanswered_question(
                    database=database,
                    assessment_id=assessment.id,
                )
            )

        if existing is None:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_409_CONFLICT
                ),
                detail=(
                    "Question generation conflicted "
                    "with another request."
                ),
            )

        return serialize_question(
            existing
        )

    return serialize_question(
        question
    )


@router.get(
    "/{assessment_id}/questions",
    response_model=list[
        QuestionResponse
    ],
)
async def list_questions(
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

    return [
        serialize_question(question)
        for question
        in assessment.questions
    ]


@router.post(
    "/{assessment_id}/questions/{question_id}/answer",
    response_model=AnswerEvaluationResponse,
)
async def submit_answer(
    assessment_id: int,
    question_id: int,
    request: SubmitAnswerRequest,
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
            detail="Assessment is not in progress.",
        )

    question = get_owned_question(
        database=database,
        user_id=current_user.id,
        assessment_id=assessment.id,
        question_id=question_id,
    )

    if question.learner_answer is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This question has already "
                "been answered."
            ),
        )

    try:
        expected_topics = json.loads(
            question.expected_topics
            or "[]"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Stored assessment metadata "
                "is invalid."
            ),
        )

    if not isinstance(
        expected_topics,
        list,
    ):
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Stored assessment metadata "
                "is invalid."
            ),
        )

    try:
        evaluation = (
            await evaluate_assessment_answer(
                model=request.model,

                program_type=(
                    assessment
                    .program
                    .program_type
                ),

                concept=(
                    question.concept
                ),

                difficulty=(
                    question.difficulty
                ),

                question_text=(
                    question.question_text
                ),

                expected_topics=(
                    expected_topics
                ),

                evaluator_notes=(
                    question.evaluator_notes
                    or ""
                ),

                learner_answer=(
                    request.answer
                ),
            )
        )

    except EvaluationError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(exc),
        )

    classification = (
        classification_from_score(
            evaluation.score
        )
    )

    previous_metadata = {}

    if question.evidence:
        try:
            parsed = json.loads(
                question.evidence
            )

            if isinstance(
                parsed,
                dict,
            ):
                previous_metadata = parsed

        except json.JSONDecodeError:
            previous_metadata = {}

    evidence = {
        **previous_metadata,

        "classification":
            classification,

        "demonstrated":
            evaluation.demonstrated,

        "gaps":
            evaluation.gaps,

        "reasoning_summary":
            evaluation.reasoning_summary,
    }

    question.learner_answer = (
        request.answer
    )

    question.score = (
        evaluation.score
    )

    question.evaluation = (
        evaluation.feedback
    )

    question.evidence = json.dumps(
        evidence
    )

    question.answered_at = (
        datetime.utcnow()
    )

    assessment.questions_answered += 1

    assessment_complete = (
        assessment.questions_answered
        >= assessment.max_questions
    )

    if assessment_complete:
        assessment.status = "completed"

        assessment.completed_at = (
            datetime.utcnow()
        )

    database.commit()
    database.refresh(question)
    database.refresh(assessment)

    return AnswerEvaluationResponse(
        question_id=question.id,

        concept=question.concept,

        difficulty=question.difficulty,

        score=question.score,

        classification=classification,

        demonstrated=(
            evaluation.demonstrated
        ),

        gaps=(
            evaluation.gaps
        ),

        feedback=(
            evaluation.feedback
        ),

        questions_answered=(
            assessment.questions_answered
        ),

        max_questions=(
            assessment.max_questions
        ),

        assessment_complete=(
            assessment_complete
        ),
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

    assessment.completed_at = (
        datetime.utcnow()
    )

    database.commit()

    return MessageResponse(
        message="Assessment abandoned."
    )