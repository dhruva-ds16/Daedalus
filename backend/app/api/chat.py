import json
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.ollama import stream_chat


router = APIRouter()


class Message(BaseModel):
    role: Literal[
        "user",
        "assistant",
    ]

    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
):

    async def generate():
        try:
            messages = [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ]

            async for event in stream_chat(
                model=request.model,
                messages=messages,
            ):
                yield (
                    json.dumps(
                        event,
                        ensure_ascii=False,
                    )
                    + "\n"
                ).encode("utf-8")

        except Exception as exc:
            error_event = {
                "type": "error",
                "message": str(exc),
            }

            yield (
                json.dumps(
                    error_event,
                    ensure_ascii=False,
                )
                + "\n"
            ).encode("utf-8")

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control":
                "no-cache, no-transform",

            "X-Accel-Buffering":
                "no",
        },
    )