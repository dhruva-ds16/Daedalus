from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.ollama import stream_chat


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    model: str


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):

    async def generate():
        try:
            async for chunk in stream_chat(
                model=request.model,
                message=request.message,
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
