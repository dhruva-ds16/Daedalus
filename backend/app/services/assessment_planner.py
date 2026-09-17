import json

import httpx

from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

from app.config import OLLAMA_URL


class PlannedQuestion(BaseModel):
    concept: str = Field(
        min_length=2,
        max_length=150,
    )

    difficulty: str = Field(
        pattern="^(beginner|intermediate|advanced)$"
    )

    question_text: str = Field(
        min_length=10,
        max_length=3000,
    )

    expected_topics: list[str] = Field(
        min_length=1,
        max_length=10,
    )

    evaluator_notes: str = Field(
        min_length=10,
        max_length=2000,
    )

    selection_reason: str = Field(
        min_length=10,
        max_length=1000,
    )


class AssessmentPlanningError(Exception):
    pass


def build_planner_prompt(
    *,
    program_type: str,
    program_goal: str | None,
    learner_experience: str,
    learner_goal: str | None,
    preferred_depth: str,
    question_number: int,
    max_questions: int,
    previous_evidence: list[dict],
) -> str:
    evidence_json = json.dumps(
        previous_evidence,
        indent=2,
    )

    return f"""
You are the diagnostic assessment planner for Daedalus,
an adaptive tutor for Rust programming and Windows Internals.

Your task is to decide the SINGLE most useful diagnostic
question to ask next.

You control the pedagogical decision:
- what concept to test
- what difficulty to use
- what question to ask
- what evidence a strong answer should contain

You are NOT generating a curriculum yet.
You are diagnosing the learner so a personalized curriculum
can be created after the assessment.

PROGRAM

Type:
{program_type}

Program goal:
{program_goal or "Not specified"}

LEARNER

Programming experience:
{learner_experience}

Overall learning goal:
{learner_goal or "Not specified"}

Preferred explanation depth:
{preferred_depth}

ASSESSMENT

Next question number:
{question_number}

Maximum questions:
{max_questions}

PREVIOUS ASSESSMENT EVIDENCE

{evidence_json}

PLANNING PRINCIPLES

- Determine useful diagnostic coverage yourself.
- Do not rely on a predefined topic list.
- Use previous evidence to decide what should be tested next.
- Avoid repeatedly testing knowledge already demonstrated strongly.
- Probe uncertain or weak areas when doing so provides useful
  diagnostic information.
- Maintain reasonable breadth across the requested subject.
- Earlier questions should establish broad foundations.
- Later questions may probe deeper based on demonstrated ability.
- Increase difficulty when previous evidence supports it.
- Reduce difficulty when the learner appears to lack prerequisite
  understanding.
- Do not assume knowledge that has not been demonstrated.
- For an integrated program, assess both conceptual Windows
  understanding and the learner's ability to connect it to Rust.
- Prefer understanding and reasoning over trivia or memorization.
- Ask ONE focused question.
- Do not provide the answer.
- Do not teach the learner inside the question.
- Do not greet the learner.
- Do not use multiple choice.
- A short code snippet is allowed when diagnostically useful.
- The question should normally be answerable in a few paragraphs
  or less.

DIFFICULTY

difficulty must be exactly one of:

beginner
intermediate
advanced

OUTPUT

Return ONLY valid JSON.

Required schema:

{{
  "concept": "specific concept being diagnosed",
  "difficulty": "beginner",
  "question_text": "question shown to the learner",
  "expected_topics": [
    "important idea a strong answer may demonstrate"
  ],
  "evaluator_notes": "hidden guidance for evaluating the answer",
  "selection_reason": "short internal explanation of why this is the best next diagnostic question"
}}
""".strip()


def extract_json_object(
    text: str,
) -> dict:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines:
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        cleaned = "\n".join(
            lines
        ).strip()

    try:
        parsed = json.loads(
            cleaned
        )

    except json.JSONDecodeError as exc:
        raise AssessmentPlanningError(
            "Assessment planner returned invalid JSON."
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise AssessmentPlanningError(
            "Assessment planner response was not a JSON object."
        )

    return parsed


async def plan_assessment_question(
    *,
    model: str,
    program_type: str,
    program_goal: str | None,
    learner_experience: str,
    learner_goal: str | None,
    preferred_depth: str,
    question_number: int,
    max_questions: int,
    previous_evidence: list[dict],
) -> PlannedQuestion:
    prompt = build_planner_prompt(
        program_type=program_type,
        program_goal=program_goal,
        learner_experience=learner_experience,
        learner_goal=learner_goal,
        preferred_depth=preferred_depth,
        question_number=question_number,
        max_questions=max_questions,
        previous_evidence=previous_evidence,
    )

    payload = {
        "model": model,

        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],

        "stream": False,

        "options": {
            "temperature": 0.2,
        },
    }

    try:
        async with httpx.AsyncClient(
            timeout=180.0
        ) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
            )

            response.raise_for_status()

    except httpx.HTTPError as exc:
        raise AssessmentPlanningError(
            "Unable to communicate with Ollama."
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise AssessmentPlanningError(
            "Ollama returned an invalid response."
        ) from exc

    content = (
        data.get(
            "message",
            {}
        ).get(
            "content",
            ""
        )
    )

    if not content:
        raise AssessmentPlanningError(
            "Assessment planner returned an empty response."
        )

    parsed = extract_json_object(
        content
    )

    try:
        return PlannedQuestion.model_validate(
            parsed
        )

    except ValidationError as exc:
        raise AssessmentPlanningError(
            "Assessment planner response failed schema validation."
        ) from exc