from datetime import datetime
from uuid import uuid4

from qdrant_client.models import (
    PointStruct,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    KnowledgeChunk,
    KnowledgeSource,
)

from app.services.knowledge_embedder import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    KnowledgeEmbeddingError,
    build_embedding_text,
    embed_texts,
)

from app.services.knowledge_vector_store import (
    KnowledgeVectorStoreError,
    delete_source_vectors,
    ensure_collection,
    upsert_points,
)


class KnowledgeIndexingError(
    Exception
):
    pass


async def index_knowledge_source(
    *,
    database: Session,
    source: KnowledgeSource,
) -> KnowledgeSource:
    if source.chunk_count <= 0:
        raise KnowledgeIndexingError(
            "Source must be chunked before indexing."
        )

    source.status = "embedding"
    source.error_message = None

    database.commit()

    try:
        ensure_collection()

        statement = (
            select(
                KnowledgeChunk
            )
            .where(
                KnowledgeChunk.source_id
                == source.id,

                KnowledgeChunk
                .retrieval_enabled
                .is_(True),
            )
            .order_by(
                KnowledgeChunk
                .chunk_index
            )
        )

        chunks = database.scalars(
            statement
        ).all()

        if not chunks:
            raise KnowledgeIndexingError(
                "No retrieval-enabled chunks were found."
            )

        # Re-index always starts clean.
        delete_source_vectors(
            source.id
        )

        for chunk in chunks:
            chunk.vector_id = None

        source.embedding_model = None
        source.indexed_at = None

        database.commit()

        for start in range(
            0,
            len(chunks),
            EMBEDDING_BATCH_SIZE,
        ):
            batch = chunks[
                start:
                start
                + EMBEDDING_BATCH_SIZE
            ]

            embedding_texts = [
                build_embedding_text(
                    source_title=(
                        source.title
                    ),

                    domain=(
                        source.domain
                    ),

                    edition=(
                        source.edition
                    ),

                    section_hint=(
                        chunk.section_hint
                    ),

                    page_start=(
                        chunk.page_start
                    ),

                    page_end=(
                        chunk.page_end
                    ),

                    text=chunk.text,
                )
                for chunk
                in batch
            ]

            vectors = await embed_texts(
                embedding_texts
            )

            points = []

            vector_ids = []

            for chunk, vector in zip(
                batch,
                vectors,
            ):
                vector_id = str(
                    uuid4()
                )

                vector_ids.append(
                    (
                        chunk,
                        vector_id,
                    )
                )

                points.append(
                    PointStruct(
                        id=vector_id,

                        vector=vector,

                        payload={
                            "source_id":
                                source.id,

                            "chunk_id":
                                chunk.id,

                            "chunk_index":
                                chunk.chunk_index,

                            "source_title":
                                source.title,

                            "domain":
                                source.domain,

                            "source_type":
                                source.source_type,

                            "authority":
                                source.authority,

                            "edition":
                                source.edition,

                            "page_start":
                                chunk.page_start,

                            "page_end":
                                chunk.page_end,

                            "section_hint":
                                chunk.section_hint,

                            "quality_score":
                                chunk.quality_score,

                            "content_type":
                                chunk.content_type,

                            "retrieval_enabled":
                                chunk.retrieval_enabled,
                        },
                    )
                )

            source.status = (
                "indexing"
            )

            database.commit()

            upsert_points(
                points
            )

            for (
                chunk,
                vector_id,
            ) in vector_ids:
                chunk.vector_id = (
                    vector_id
                )

            database.commit()

        source.status = "ready"

        source.embedding_model = (
            EMBEDDING_MODEL
        )

        source.indexed_at = (
            datetime.utcnow()
        )

        source.error_message = None

        database.commit()

        database.refresh(
            source
        )

        return source

    except (
        KnowledgeEmbeddingError,
        KnowledgeVectorStoreError,
        KnowledgeIndexingError,
    ) as exc:
        database.rollback()

        refreshed = database.get(
            KnowledgeSource,
            source.id,
        )

        if refreshed is not None:
            refreshed.status = (
                "failed"
            )

            refreshed.error_message = (
                str(exc)[:2000]
            )

            database.commit()

        raise KnowledgeIndexingError(
            str(exc)
        ) from exc

    except Exception as exc:
        database.rollback()

        refreshed = database.get(
            KnowledgeSource,
            source.id,
        )

        if refreshed is not None:
            refreshed.status = (
                "failed"
            )

            refreshed.error_message = (
                str(exc)[:2000]
            )

            database.commit()

        raise KnowledgeIndexingError(
            f"Knowledge indexing failed: {exc}"
        ) from exc