import json

import httpx

from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

from app.config import OLLAMA_URL


class GeneratedEvaluation(BaseModel):
    score: float = Field(
        ge=0.0,
        le=1.0,
    )

    demonstrated: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    gaps: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    feedback: str = Field(
        min_length=1,
        max_length=2000,
    )

    reasoning_summary: str = Field(
        min_length=1,
        max_length=2000,
    )


class EvaluationError(Exception):
    pass


def classification_from_score(
    score: float,
) -> str:
    if score < 0.25:
        return "weak"

    if score < 0.50:
        return "developing"

    if score < 0.75:
        return "competent"

    return "strong"


def build_evaluation_prompt(
    program_type: str,
    concept: str,
    difficulty: str,
    question_text: str,
    expected_topics: list[str],
    evaluator_notes: str,
    learner_answer: str,
) -> str:
    expected = "\n".join(
        f"- {topic}"
        for topic in expected_topics
    )

    return f"""
You are evaluating ONE answer from a diagnostic learning assessment.

Program:
{program_type}

Concept:
{concept}

Difficulty:
{difficulty}

Question:
{question_text}

Important ideas a strong answer may demonstrate:
{expected}

Evaluator guidance:
{evaluator_notes}

Learner answer:
{learner_answer}

Evaluate the learner's demonstrated understanding of the concept.

Scoring:
0.00 = no meaningful understanding demonstrated
0.25 = limited or substantially incorrect understanding
0.50 = partial but useful understanding
0.75 = strong understanding with minor gaps
1.00 = accurate and complete for the requested difficulty

Rules:
- Evaluate only what the learner actually demonstrated.
- Do not reward verbosity.
- Do not punish concise but correct answers.
- Identify misconceptions as gaps.
- Do not invent knowledge the learner did not demonstrate.
- Be tolerant of wording differences.
- Judge against the requested difficulty.
- feedback is shown to the learner.
- reasoning_summary is internal and should be concise.
- Do not include a classification. The application derives it from score.

Return ONLY valid JSON.

Required schema:

{{
  "score": 0.0,
  "demonstrated": [
    "knowledge demonstrated by the learner"
  ],
  "gaps": [
    "missing or incorrect concept"
  ],
  "feedback": "short constructive feedback for the learner",
  "reasoning_summary": "short internal explanation of the score"
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
        raise EvaluationError(
            "Evaluator returned invalid JSON."
        ) from exc

    if not isinstance(
        parsed,
        dict,
    ):
        raise EvaluationError(
            "Evaluator response was not a JSON object."
        )

    return parsed


async def evaluate_assessment_answer(
    model: str,
    program_type: str,
    concept: str,
    difficulty: str,
    question_text: str,
    expected_topics: list[str],
    evaluator_notes: str,
    learner_answer: str,
) -> GeneratedEvaluation:
    prompt = build_evaluation_prompt(
        program_type=program_type,
        concept=concept,
        difficulty=difficulty,
        question_text=question_text,
        expected_topics=expected_topics,
        evaluator_notes=evaluator_notes,
        learner_answer=learner_answer,
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
            "temperature": 0.1,
        },
    }

    try:
        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
            )

            response.raise_for_status()

    except httpx.HTTPError as exc:
        raise EvaluationError(
            "Unable to communicate with Ollama."
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise EvaluationError(
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
        raise EvaluationError(
            "Evaluator returned an empty response."
        )

    parsed = extract_json_object(
        content
    )

    try:
        return GeneratedEvaluation.model_validate(
            parsed
        )

    except ValidationError as exc:
        raise EvaluationError(
            "Evaluator response failed schema validation."
        ) from exc