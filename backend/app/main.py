from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.database import router as database_router
from app.api.health import router as health_router
from app.api.models import router as models_router

from app.config import (
    APP_NAME,
    APP_VERSION,
)

from app.database import initialize_database


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    initialize_database()

    yield


app = FastAPI(
    title=APP_NAME,
    description=(
        "Adaptive AI tutor for Windows Internals "
        "and Rust programming"
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)


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


app.include_router(
    health_router
)

app.include_router(
    models_router
)

app.include_router(
    chat_router
)

app.include_router(
    database_router
)

app.include_router(
    auth_router
)


@app.get("/")
async def root():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
    }