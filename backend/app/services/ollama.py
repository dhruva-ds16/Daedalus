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
                "modified_at": model.get("modified_at"),
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

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_URL}/api/chat",
            json=payload,
        ) as response:

            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line:
                    continue

                data = json.loads(line)

                content = (
                    data
                    .get("message", {})
                    .get("content", "")
                )

                if content:
                    yield content
