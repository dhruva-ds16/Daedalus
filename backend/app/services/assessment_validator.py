import json

import httpx

from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

from app.config import OLLAMA_URL


class ValidationResult(BaseModel):
    approved: bool

    factual_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    clarity_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    rubric_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    difficulty_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    issues: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    rejection_reason: str | None = Field(
        default=None,
        max_length=2000,
    )


class AssessmentValidationError(Exception):
    pass


def build_validation_prompt(
    *,
    program_type: str,
    concept: str,
    difficulty: str,
    question_text: str,
    expected_topics: list[str],
    evaluator_notes: str,
) -> str:
    expected_json = json.dumps(
        expected_topics,
        indent=2,
    )

    return f"""
You are the quality-control reviewer for a diagnostic
assessment question.

The question was generated for this learning program:

Program:
{program_type}

Concept:
{concept}

Difficulty:
{difficulty}

Question:
{question_text}

Expected topics:
{expected_json}

Evaluator guidance:
{evaluator_notes}

Review the candidate BEFORE it is shown to the learner.

Check all of the following:

1. FACTUAL CORRECTNESS
- The question must not rely on false technical premises.
- The expected topics must be technically correct.
- The evaluator guidance must be technically correct.
- Reject claims that are architecture-specific but presented
  as universally true.
- Reject outdated assumptions presented as general modern facts.

2. QUESTION / RUBRIC CONSISTENCY
- The expected topics must actually answer the question.
- The evaluator must not expect unrelated knowledge.
- A technically correct learner answer must not be penalized
  because the hidden rubric contains a false premise.

3. CLARITY
- The question must be understandable.
- It must not contain contradictory assumptions.
- It should primarily test one coherent area.
- It must not accidentally reveal the answer.

4. DIAGNOSTIC VALUE
- The question should test understanding rather than trivia.
- The requested difficulty should approximately match the
  cognitive demands of the question.
- The learner should normally be able to answer in a few
  paragraphs or less.

5. PROGRAM RELEVANCE
- The question must be useful for diagnosing the learner
  within the requested program.
- For integrated programs, a Windows/Rust connection is useful
  when pedagogically appropriate, but every question does not
  need to combine both subjects.

Be critical.

If there is a material factual error, set approved to false.

If the hidden grading rubric contains a material factual error,
set approved to false even when the visible question looks valid.

Scores range from 0.0 to 1.0.

approved should normally require:
- factual_score >= 0.85
- clarity_score >= 0.70
- rubric_score >= 0.80
- difficulty_score >= 0.65
- no material factual issue

Return ONLY valid JSON.

Required schema:

{{
  "approved": true,
  "factual_score": 0.95,
  "clarity_score": 0.90,
  "rubric_score": 0.95,
  "difficulty_score": 0.85,
  "issues": [],
  "rejection_reason": null
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
        raise AssessmentValidationError(
            "Assessment validator returned invalid JSON."
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise AssessmentValidationError(
            "Assessment validator response was not a JSON object."
        )

    return parsed


async def validate_assessment_question(
    *,
    model: str,
    program_type: str,
    concept: str,
    difficulty: str,
    question_text: str,
    expected_topics: list[str],
    evaluator_notes: str,
) -> ValidationResult:
    prompt = build_validation_prompt(
        program_type=program_type,
        concept=concept,
        difficulty=difficulty,
        question_text=question_text,
        expected_topics=expected_topics,
        evaluator_notes=evaluator_notes,
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
            "temperature": 0.0,
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
        raise AssessmentValidationError(
            "Unable to communicate with Ollama during validation."
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise AssessmentValidationError(
            "Ollama returned an invalid validation response."
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
        raise AssessmentValidationError(
            "Assessment validator returned an empty response."
        )

    parsed = extract_json_object(
        content
    )

    try:
        result = ValidationResult.model_validate(
            parsed
        )

    except ValidationError as exc:
        raise AssessmentValidationError(
            "Assessment validator response failed schema validation."
        ) from exc

    server_approved = (
        result.approved
        and result.factual_score >= 0.85
        and result.clarity_score >= 0.70
        and result.rubric_score >= 0.80
        and result.difficulty_score >= 0.65
    )

    if result.approved != server_approved:
        result.approved = server_approved

        if (
            not server_approved
            and not result.rejection_reason
        ):
            result.rejection_reason = (
                "Candidate did not satisfy "
                "Daedalus validation thresholds."
            )

    return result