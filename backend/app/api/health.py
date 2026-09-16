from fastapi import APIRouter

from app.services.ollama import check_ollama


router = APIRouter()


@router.get("/health")
async def health():
    ollama_online = await check_ollama()

    return {
        "backend": "online",
        "ollama": (
            "online"
            if ollama_online
            else "offline"
        ),
    }
