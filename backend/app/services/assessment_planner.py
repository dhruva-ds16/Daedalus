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
    rejected_candidates: list[dict],
) -> str:
    evidence_json = json.dumps(
        previous_evidence,
        indent=2,
    )

    rejected_json = json.dumps(
        rejected_candidates,
        indent=2,
    )

    remaining = (
        max_questions
        - question_number
        + 1
    )

    return f"""
You are the diagnostic assessment planner for Daedalus,
an adaptive tutor for Rust programming and Windows Internals.

Your task is to choose the SINGLE most useful diagnostic
question to ask next.

You determine:
- what concept should be tested
- the appropriate difficulty
- the question itself
- what evidence a strong answer may contain
- hidden evaluator guidance

You are NOT generating the learner's curriculum yet.

Your goal is to collect enough reliable evidence that a
personalized curriculum can be generated after the assessment.

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

ASSESSMENT STATE

Next question:
{question_number}

Maximum questions:
{max_questions}

Question opportunities remaining including this one:
{remaining}

PREVIOUS EVIDENCE

{evidence_json}

REJECTED CANDIDATES FROM THIS PLANNING ATTEMPT

{rejected_json}

DIAGNOSTIC STRATEGY

You must decide appropriate subject coverage yourself.
There is no predefined topic list.

Use the limited question budget intelligently.

Balance BREADTH and DEPTH:

- Early in the assessment, prefer broad diagnostic coverage
  across materially different areas of the subject.
- Do not repeatedly test the same conceptual neighborhood
  simply because previous evidence exists there.
- Strong evidence usually means another basic question on the
  same topic has low diagnostic value.
- Weak evidence may justify ONE useful prerequisite or
  clarification probe when it materially improves diagnosis.
- Repeatedly asking minor variations of the same concept wastes
  the assessment budget.
- As the assessment progresses, deepen areas where uncertainty
  remains or where advanced knowledge needs confirmation.
- Consider what important areas remain unknown.
- Use the remaining question budget to produce a useful overall
  knowledge estimate rather than exhaustive coverage.

DIFFICULTY ADAPTATION

- Increase difficulty when demonstrated knowledge supports it.
- Reduce difficulty when prerequisite understanding appears weak.
- Do not assume knowledge that has not been demonstrated.
- Difficulty must reflect the actual cognitive demands of the
  question, not merely the technical vocabulary used.

INTEGRATED PROGRAMS

For an integrated Windows + Rust program:

- Diagnose both Windows understanding and Rust understanding.
- Also diagnose the learner's ability to connect the two.
- Do NOT force every question to combine Windows and Rust.
- Some questions may focus primarily on Windows.
- Some may focus primarily on Rust.
- Some should test the integration between them.
- Avoid repeatedly asking variants of resource lifetime,
  handles, ownership, or borrowing if those areas have already
  been adequately sampled.

QUESTION QUALITY

- Ask ONE focused diagnostic question.
- Prefer reasoning and mental models over trivia.
- Do not provide the answer.
- Do not teach inside the question.
- Do not greet the learner.
- Do not use multiple choice.
- Avoid false premises.
- Avoid architecture-specific claims presented as universal facts.
- Avoid outdated assumptions presented as general modern behavior.
- A short code snippet is allowed when diagnostically useful.
- The learner should normally be able to answer in a few
  paragraphs or less.

REJECTED CANDIDATES

If rejected_candidates is non-empty:
- Do not regenerate substantially the same candidate.
- Read the validator issues and correct them.
- Select another concept when the rejection indicates the
  previous concept framing was problematic.

DIFFICULTY

Use exactly one:

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
  "evaluator_notes": "hidden technically accurate grading guidance",
  "selection_reason": "internal explanation of why this diagnostic probe is useful now"
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
    rejected_candidates: list[dict] | None = None,
) -> PlannedQuestion:
    rejected_candidates = (
        rejected_candidates
        or []
    )

    prompt = build_planner_prompt(
        program_type=program_type,
        program_goal=program_goal,
        learner_experience=learner_experience,
        learner_goal=learner_goal,
        preferred_depth=preferred_depth,
        question_number=question_number,
        max_questions=max_questions,
        previous_evidence=previous_evidence,
        rejected_candidates=rejected_candidates,
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
            {},
        ).get(
            "content",
            "",
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