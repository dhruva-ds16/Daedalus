from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json


app = FastAPI(
    title="Daedalus",
    description="Local AI tutor for Windows Internals and Rust",
    version="0.2.0",
)

OLLAMA_URL = "http://localhost:11434"


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Models
# ---------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    model: str


# ---------------------------------------------------------
# Tutor Prompt
# ---------------------------------------------------------

SYSTEM_PROMPT = """
You are Daedalus, a personal AI tutor specializing in:

1. Windows Internals
2. Rust programming
3. Systems programming

The learner is developing their systems-programming knowledge.

Your teaching principles:

- Explain concepts clearly.
- Build strong mental models.
- Introduce terminology gradually.
- Use practical examples.
- Connect Rust concepts to Windows Internals where appropriate.
- Prefer understanding over memorization.
- Do not overwhelm the learner with unnecessary information.
- When teaching, explain why something works rather than only what it does.

Your name is Daedalus.
"""


# ---------------------------------------------------------
# Root
# ---------------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": "Daedalus",
        "version": "0.2.0",
        "status": "running",
    }


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OLLAMA_URL}/api/tags",
                timeout=5,
            )

        response.raise_for_status()

        return {
            "backend": "online",
            "ollama": "online",
        }

    except Exception:
        return {
            "backend": "online",
            "ollama": "offline",
        }


# ---------------------------------------------------------
# Normal non-streaming chat
# ---------------------------------------------------------

@app.post("/chat")
async def chat(request: ChatRequest):
    payload = {
        "model": request.model,
        "keep_alive": "30m",
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": request.message,
            },
        ],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
        )

        response.raise_for_status()
        result = response.json()

    return {
        "response": result["message"]["content"],
        "metrics": {
            "total_duration_ms": round(
                result.get("total_duration", 0) / 1_000_000,
                2,
            ),
            "load_duration_ms": round(
                result.get("load_duration", 0) / 1_000_000,
                2,
            ),
            "prompt_tokens": result.get(
                "prompt_eval_count",
                0,
            ),
            "prompt_duration_ms": round(
                result.get("prompt_eval_duration", 0) / 1_000_000,
                2,
            ),
            "generated_tokens": result.get(
                "eval_count",
                0,
            ),
            "generation_duration_ms": round(
                result.get("eval_duration", 0) / 1_000_000,
                2,
            ),
        },
    }


# ---------------------------------------------------------
# Streaming chat
# ---------------------------------------------------------

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):

    async def generate():
        payload = {
            "model": request.model,
            "keep_alive": "30m",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": request.message,
                },
            ],
            "stream": True,
        }

        try:
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

                        message = data.get("message", {})
                        content = message.get("content", "")

                        if content:
                            yield content

        except Exception as exc:
            yield f"\n\n[Daedalus streaming error: {str(exc)}]"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )
