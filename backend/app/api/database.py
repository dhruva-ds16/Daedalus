from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import DATABASE_PATH
from app.database.session import get_db


router = APIRouter()


@router.get("/database/health")
async def database_health(
    database: Session = Depends(get_db),
):
    try:
        database.execute(
            text("SELECT 1")
        )

        return {
            "database": "online",
            "engine": "sqlite",
            "path": str(DATABASE_PATH),
        }

    except Exception as exc:
        return {
            "database": "offline",
            "error": str(exc),
        }