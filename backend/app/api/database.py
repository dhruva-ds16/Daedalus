from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.models import User
from app.database.session import get_db


router = APIRouter()


@router.get("/database/health")
async def database_health(
    database: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    try:
        database.execute(
            text("SELECT 1")
        )

        return {
            "database": "online",
            "engine": "sqlite",
        }

    except Exception as exc:
        return {
            "database": "offline",
            "error": str(exc),
        }