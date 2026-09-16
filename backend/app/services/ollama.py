import json

import httpx

from app.config import (
    OLLAMA_KEEP_ALIVE,
    OLLAMA_URL,
    SYSTEM_PROMPT,
)


async def check_ollama():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{OLLAMA_URL}/api/tags"
            )
            response.raise_for_status()

        return True

    except Exception:
        return False


async def get_models():
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{OLLAMA_URL}/api/tags"
        )
        response.raise_for_status()

        data = response.json()

    models = []

    for model in data.get("models", []):
        models.append(
            {
                "name": model.get("name"),
                "size": model.get("size"),
                "modified_at": model.get(
                    "modified_at"
                ),
            }
        )

    return models


async def stream_chat(
    model: str,
    messages: list[dict],
):
    ollama_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    ollama_messages.extend(messages)

    payload = {
        "model": model,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "messages": ollama_messages,
        "stream": True,
    }

    timeout = httpx.Timeout(
        connect=10.0,
        read=None,
        write=30.0,
        pool=10.0,
    )

    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        async with client.stream(
            "POST",
            f"{OLLAMA_URL}/api/chat",
            json=payload,
        ) as response:

            response.raise_for_status()

            buffer = b""

            async for chunk in response.aiter_raw():
                if not chunk:
                    continue

                buffer += chunk

                while b"\n" in buffer:
                    line, buffer = buffer.split(
                        b"\n",
                        1,
                    )

                    if not line.strip():
                        continue

                    data = json.loads(
                        line.decode("utf-8")
                    )

                    content = (
                        data
                        .get("message", {})
                        .get("content", "")
                    )

                    if content:
                        yield {
                            "type": "token",
                            "content": content,
                        }

                    if data.get("done"):
                        eval_count = data.get(
                            "eval_count",
                            0,
                        )

                        eval_duration = data.get(
                            "eval_duration",
                            0,
                        )

                        total_duration = data.get(
                            "total_duration",
                            0,
                        )

                        load_duration = data.get(
                            "load_duration",
                            0,
                        )

                        prompt_eval_count = data.get(
                            "prompt_eval_count",
                            0,
                        )

                        prompt_eval_duration = data.get(
                            "prompt_eval_duration",
                            0,
                        )

                        tokens_per_second = 0

                        if eval_duration:
                            seconds = (
                                eval_duration
                                / 1_000_000_000
                            )

                            if seconds > 0:
                                tokens_per_second = (
                                    eval_count
                                    / seconds
                                )

                        yield {
                            "type": "metrics",
                            "metrics": {
                                "generated_tokens":
                                    eval_count,

                                "tokens_per_second":
                                    round(
                                        tokens_per_second,
                                        2,
                                    ),

                                "total_duration_ms":
                                    round(
                                        total_duration
                                        / 1_000_000,
                                        2,
                                    ),

                                "load_duration_ms":
                                    round(
                                        load_duration
                                        / 1_000_000,
                                        2,
                                    ),

                                "prompt_tokens":
                                    prompt_eval_count,

                                "prompt_duration_ms":
                                    round(
                                        prompt_eval_duration
                                        / 1_000_000,
                                        2,
                                    ),
                            },
                        }