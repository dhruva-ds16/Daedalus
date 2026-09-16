from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.ollama import stream_chat


router = APIRouter()


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):

    async def generate():
        try:
            messages = [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ]

            async for chunk in stream_chat(
                model=request.model,
                messages=messages,
            ):
                yield chunk

        except Exception as exc:
            yield (
                "\n\n"
                f"[Daedalus streaming error: {str(exc)}]"
            )

    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )
