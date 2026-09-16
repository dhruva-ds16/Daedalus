from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from app.api.dependencies import get_current_user
from app.database.models import User
from app.services.ollama import get_models


router = APIRouter()


@router.get("/models")
async def models(
    current_user: User = Depends(
        get_current_user
    ),
):
    try:
        available_models = await get_models()

        return {
            "models": available_models,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to retrieve "
                f"Ollama models: {exc}"
            ),
        )