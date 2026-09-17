import hashlib

from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status

from pydantic import BaseModel

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user

from app.database.models import KnowledgeChunk
from app.database.models import KnowledgePage
from app.database.models import KnowledgeSource
from app.database.models import User

from app.database.session import get_db

from app.services.knowledge_extractor import (
    KnowledgeExtractionError,
    extract_knowledge_source,
)

from app.services.knowledge_chunker import (
    KnowledgeChunkingError,
    chunk_knowledge_source,
)

router = APIRouter(
    prefix="/admin/knowledge",
    tags=["Admin Knowledge Base"],
)


KNOWLEDGE_ROOT = Path(
    "/home/dhruva/daedalus/data/knowledge"
)

ORIGINALS_DIRECTORY = (
    KNOWLEDGE_ROOT / "originals"
)


MAX_FILE_SIZE = (
    500 * 1024 * 1024
)


ALLOWED_EXTENSIONS = {
    ".pdf",
}


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/octet-stream",
}


Domain = Literal[
    "windows",
    "rust",
    "integrated",
    "general",
]


SourceType = Literal[
    "textbook",
    "documentation",
    "reference",
    "supplementary",
]


Authority = Literal[
    "authoritative",
    "trusted",
    "supplementary",
]


KnowledgeStatus = Literal[
    "uploaded",
    "extracting",
    "extracted",
    "chunking",
    "chunked",
    "embedding",
    "indexing",
    "ready",
    "failed",
]


class KnowledgeSourceResponse(
    BaseModel
):
    id: int

    uploaded_by_user_id: int

    title: str

    original_filename: str

    file_type: str
    mime_type: str
    file_size: int

    domain: str
    source_type: str
    authority: str

    edition: str | None
    notes: str | None

    status: str
    enabled: bool

    page_count: int | None
    chunk_count: int

    embedding_model: str | None
    error_message: str | None

    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None


class KnowledgePageSummaryResponse(
    BaseModel
):
    id: int

    page_number: int

    character_count: int
    word_count: int

    has_text: bool


class KnowledgePageDetailResponse(
    KnowledgePageSummaryResponse
):
    text: str

class KnowledgeChunkSummaryResponse(
    BaseModel
):
    id: int
    chunk_index: int

    page_start: int
    page_end: int

    content_type: str

    section_hint: str | None

    character_count: int
    word_count: int

    quality_score: float

    retrieval_enabled: bool


class KnowledgeChunkDetailResponse(
    KnowledgeChunkSummaryResponse
):
    text: str

class MessageResponse(
    BaseModel
):
    message: str


def require_admin(
    current_user: User = Depends(
        get_current_user
    ),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Administrator access required."
            ),
        )

    return current_user


def serialize_source(
    source: KnowledgeSource,
) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(
        id=source.id,

        uploaded_by_user_id=(
            source.uploaded_by_user_id
        ),

        title=source.title,

        original_filename=(
            source.original_filename
        ),

        file_type=source.file_type,
        mime_type=source.mime_type,
        file_size=source.file_size,

        domain=source.domain,

        source_type=(
            source.source_type
        ),

        authority=source.authority,

        edition=source.edition,
        notes=source.notes,

        status=source.status,
        enabled=source.enabled,

        page_count=source.page_count,
        chunk_count=source.chunk_count,

        embedding_model=(
            source.embedding_model
        ),

        error_message=(
            source.error_message
        ),

        created_at=source.created_at,
        updated_at=source.updated_at,

        indexed_at=source.indexed_at,
    )


def get_source(
    database: Session,
    source_id: int,
) -> KnowledgeSource:
    source = database.get(
        KnowledgeSource,
        source_id,
    )

    if source is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Knowledge source not found."
            ),
        )

    return source


def ensure_directories() -> None:
    ORIGINALS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


@router.get(
    "/sources",
    response_model=list[
        KnowledgeSourceResponse
    ],
)
async def list_sources(
    database: Session = Depends(
        get_db
    ),
    admin: User = Depends(
        require_admin
    ),
):
    statement = (
        select(KnowledgeSource)
        .order_by(
            KnowledgeSource
            .created_at
            .desc()
        )
    )

    sources = database.scalars(
        statement
    ).all()

    return [
        serialize_source(
            source
        )
        for source in sources
    ]


@router.get(
    "/sources/{source_id}",
    response_model=(
        KnowledgeSourceResponse
    ),
)
async def read_source(
    source_id: int,
    database: Session = Depends(
        get_db
    ),
    admin: User = Depends(
        require_admin
    ),
):
    source = get_source(
        database=database,
        source_id=source_id,
    )

    return serialize_source(
        source
    )


@router.post(
    "/sources",
    response_model=(
        KnowledgeSourceResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def upload_source(
    title: str = Form(...),

    domain: Domain = Form(...),

    source_type: SourceType = Form(
        ...
    ),

    authority: Authority = Form(
        ...
    ),

    edition: str | None = Form(
        default=None
    ),

    notes: str | None = Form(
        default=None
    ),

    file: UploadFile = File(...),

    database: Session = Depends(
        get_db
    ),

    admin: User = Depends(
        require_admin
    ),
):
    ensure_directories()

    clean_title = (
        title.strip()
    )

    if not clean_title:
        raise HTTPException(
            status_code=(
                status
                .HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail="Title is required.",
        )

    original_filename = (
        file.filename
        or "document.pdf"
    )

    suffix = Path(
        original_filename
    ).suffix.lower()

    if (
        suffix
        not in ALLOWED_EXTENSIONS
    ):
        raise HTTPException(
            status_code=(
                status
                .HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ),
            detail=(
                "Only PDF documents are "
                "supported in this version."
            ),
        )

    mime_type = (
        file.content_type
        or "application/octet-stream"
    )

    if (
        mime_type
        not in ALLOWED_MIME_TYPES
    ):
        raise HTTPException(
            status_code=(
                status
                .HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ),
            detail=(
                "Unsupported document MIME type."
            ),
        )

    stored_filename = (
        f"{uuid4().hex}.pdf"
    )

    destination = (
        ORIGINALS_DIRECTORY
        / stored_filename
    )

    sha256 = hashlib.sha256()

    total_size = 0

    try:
        with destination.open(
            "wb"
        ) as output:

            while True:
                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_size += len(
                    chunk
                )

                if (
                    total_size
                    > MAX_FILE_SIZE
                ):
                    raise HTTPException(
                        status_code=(
                            status
                            .HTTP_413_CONTENT_TOO_LARGE
                        ),
                        detail=(
                            "File exceeds the "
                            "500 MB upload limit."
                        ),
                    )

                sha256.update(
                    chunk
                )

                output.write(
                    chunk
                )

    except Exception:
        if destination.exists():
            destination.unlink()

        raise

    finally:
        await file.close()

    if total_size == 0:
        if destination.exists():
            destination.unlink()

        raise HTTPException(
            status_code=(
                status
                .HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Uploaded file is empty."
            ),
        )

    file_hash = (
        sha256.hexdigest()
    )

    existing_statement = (
        select(KnowledgeSource)
        .where(
            KnowledgeSource.file_hash
            == file_hash
        )
    )

    existing = database.scalar(
        existing_statement
    )

    if existing is not None:
        if destination.exists():
            destination.unlink()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "This document already exists "
                f"as knowledge source "
                f"'{existing.title}' "
                f"(ID {existing.id})."
            ),
        )

    source = KnowledgeSource(
        uploaded_by_user_id=(
            admin.id
        ),

        title=clean_title,

        original_filename=(
            original_filename
        ),

        stored_filename=(
            stored_filename
        ),

        file_type="pdf",

        mime_type=mime_type,

        file_size=total_size,

        file_hash=file_hash,

        domain=domain,

        source_type=source_type,

        authority=authority,

        edition=(
            edition.strip()
            if edition
            and edition.strip()
            else None
        ),

        notes=(
            notes.strip()
            if notes
            and notes.strip()
            else None
        ),

        status="uploaded",

        enabled=True,

        file_path=str(
            destination.resolve()
        ),

        page_count=None,

        chunk_count=0,

        embedding_model=None,

        error_message=None,

        indexed_at=None,
    )

    database.add(
        source
    )

    try:
        database.commit()

        database.refresh(
            source
        )

    except Exception:
        database.rollback()

        if destination.exists():
            destination.unlink()

        raise

    return serialize_source(
        source
    )


@router.post(
    "/sources/{source_id}/extract",
    response_model=(
        KnowledgeSourceResponse
    ),
)
async def extract_source(
    source_id: int,

    database: Session = Depends(
        get_db
    ),

    admin: User = Depends(
        require_admin
    ),
):
    source = get_source(
        database=database,
        source_id=source_id,
    )

    try:
        extracted = (
            extract_knowledge_source(
                database=database,
                source=source,
            )
        )

    except KnowledgeExtractionError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        )

    return serialize_source(
        extracted
    )


@router.get(
    "/sources/{source_id}/pages",
    response_model=list[
        KnowledgePageSummaryResponse
    ],
)
async def list_source_pages(
    source_id: int,

    database: Session = Depends(
        get_db
    ),

    admin: User = Depends(
        require_admin
    ),
):
    get_source(
        database=database,
        source_id=source_id,
    )

    statement = (
        select(KnowledgePage)
        .where(
            KnowledgePage.source_id
            == source_id
        )
        .order_by(
            KnowledgePage.page_number
        )
    )

    pages = database.scalars(
        statement
    ).all()

    return [
        KnowledgePageSummaryResponse(
            id=page.id,

            page_number=(
                page.page_number
            ),

            character_count=(
                page.character_count
            ),

            word_count=(
                page.word_count
            ),

            has_text=(
                page.has_text
            ),
        )
        for page in pages
    ]


@router.get(
    "/sources/{source_id}/pages/{page_number}",
    response_model=(
        KnowledgePageDetailResponse
    ),
)
async def read_source_page(
    source_id: int,
    page_number: int,

    database: Session = Depends(
        get_db
    ),

    admin: User = Depends(
        require_admin
    ),
):
    get_source(
        database=database,
        source_id=source_id,
    )

    statement = (
        select(KnowledgePage)
        .where(
            KnowledgePage.source_id
            == source_id,

            KnowledgePage.page_number
            == page_number,
        )
    )

    page = database.scalar(
        statement
    )

    if page is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Extracted page not found."
            ),
        )

    return KnowledgePageDetailResponse(
        id=page.id,

        page_number=(
            page.page_number
        ),

        character_count=(
            page.character_count
        ),

        word_count=(
            page.word_count
        ),

        has_text=(
            page.has_text
        ),

        text=page.text,
    )

@router.post(
    "/sources/{source_id}/chunk",
    response_model=KnowledgeSourceResponse,
)
async def chunk_source(
    source_id: int,

    database: Session = Depends(
        get_db
    ),

    admin: User = Depends(
        require_admin
    ),
):
    source = get_source(
        database=database,
        source_id=source_id,
    )

    try:
        chunked = (
            chunk_knowledge_source(
                database=database,
                source=source,
            )
        )

    except KnowledgeChunkingError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        )

    return serialize_source(
        chunked
    )


@router.get(
    "/sources/{source_id}/chunks",
    response_model=list[
        KnowledgeChunkSummaryResponse
    ],
)
async def list_source_chunks(
    source_id: int,

    database: Session = Depends(
        get_db
    ),

    admin: User = Depends(
        require_admin
    ),
):
    get_source(
        database=database,
        source_id=source_id,
    )

    statement = (
        select(KnowledgeChunk)
        .where(
            KnowledgeChunk.source_id
            == source_id
        )
        .order_by(
            KnowledgeChunk.chunk_index
        )
    )

    chunks = database.scalars(
        statement
    ).all()

    return [
        KnowledgeChunkSummaryResponse(
            id=chunk.id,

            chunk_index=(
                chunk.chunk_index
            ),

            page_start=(
                chunk.page_start
            ),

            page_end=(
                chunk.page_end
            ),

            content_type=(
                chunk.content_type
            ),

            section_hint=(
                chunk.section_hint
            ),

            character_count=(
                chunk.character_count
            ),

            word_count=(
                chunk.word_count
            ),

            quality_score=(
                chunk.quality_score
            ),

            retrieval_enabled=(
                chunk.retrieval_enabled
            ),
        )
        for chunk in chunks
    ]


@router.get(
    "/sources/{source_id}/chunks/{chunk_index}",
    response_model=(
        KnowledgeChunkDetailResponse
    ),
)
async def read_source_chunk(
    source_id: int,
    chunk_index: int,

    database: Session = Depends(
        get_db
    ),

    admin: User = Depends(
        require_admin
    ),
):
    get_source(
        database=database,
        source_id=source_id,
    )

    statement = (
        select(KnowledgeChunk)
        .where(
            KnowledgeChunk.source_id
            == source_id,

            KnowledgeChunk.chunk_index
            == chunk_index,
        )
    )

    chunk = database.scalar(
        statement
    )

    if chunk is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Knowledge chunk not found."
            ),
        )

    return KnowledgeChunkDetailResponse(
        id=chunk.id,

        chunk_index=(
            chunk.chunk_index
        ),

        page_start=(
            chunk.page_start
        ),

        page_end=(
            chunk.page_end
        ),

        content_type=(
            chunk.content_type
        ),

        section_hint=(
            chunk.section_hint
        ),

        character_count=(
            chunk.character_count
        ),

        word_count=(
            chunk.word_count
        ),

        quality_score=(
            chunk.quality_score
        ),

        retrieval_enabled=(
            chunk.retrieval_enabled
        ),

        text=chunk.text,
    )

@router.post(
    "/sources/{source_id}/toggle",
    response_model=(
        KnowledgeSourceResponse
    ),
)
async def toggle_source(
    source_id: int,

    database: Session = Depends(
        get_db
    ),

    admin: User = Depends(
        require_admin
    ),
):
    source = get_source(
        database=database,
        source_id=source_id,
    )

    source.enabled = (
        not source.enabled
    )

    database.commit()

    database.refresh(
        source
    )

    return serialize_source(
        source
    )


@router.delete(
    "/sources/{source_id}",
    response_model=MessageResponse,
)
async def delete_source(
    source_id: int,

    database: Session = Depends(
        get_db
    ),

    admin: User = Depends(
        require_admin
    ),
):
    source = get_source(
        database=database,
        source_id=source_id,
    )

    file_path = Path(
        source.file_path
    )

    title = source.title

    database.execute(
        delete(
            KnowledgeChunk
        ).where(
            KnowledgeChunk.source_id
            == source.id
        )
    )
    database.execute(
        delete(
            KnowledgePage
        ).where(
            KnowledgePage.source_id
            == source.id
        )
    )

    database.delete(
        source
    )

    database.commit()

    try:
        if file_path.exists():
            file_path.unlink()

    except OSError:
        pass

    return MessageResponse(
        message=(
            f"Knowledge source "
            f"'{title}' deleted."
        )
    )