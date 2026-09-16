from fastapi import APIRouter, HTTPException

from app.services.ollama import get_models


router = APIRouter()


@router.get("/models")
async def models():
    try:
        available_models = await get_models()

        return {
            "models": available_models,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to retrieve Ollama models: {exc}",
        )
