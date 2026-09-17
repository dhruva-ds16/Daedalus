from dataclasses import dataclass

from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
)

from sqlalchemy.orm import Session

from app.database.models import (
    KnowledgeChunk,
    KnowledgeSource,
)

from app.services.knowledge_embedder import (
    KnowledgeEmbeddingError,
    embed_texts,
)

from app.services.knowledge_vector_store import (
    COLLECTION_NAME,
    KnowledgeVectorStoreError,
    ensure_collection,
    get_qdrant_client,
)


DEFAULT_LIMIT = 5
MAX_LIMIT = 20

# Retrieve more candidates than we ultimately
# return so application-level ranking has room
# to work.
CANDIDATE_MULTIPLIER = 4


AUTHORITY_WEIGHTS = {
    "authoritative": 1.00,
    "trusted": 0.97,
    "supplementary": 0.92,
}


@dataclass
class RetrievalResult:
    chunk_id: int
    chunk_index: int

    source_id: int
    source_title: str

    domain: str
    source_type: str
    authority: str
    edition: str | None

    page_start: int
    page_end: int

    section_hint: str | None

    text: str

    semantic_score: float
    quality_score: float
    authority_weight: float
    final_score: float


class KnowledgeRetrievalError(
    Exception
):
    pass


def quality_weight(
    quality_score: float,
) -> float:
    """
    Quality influences ranking without completely
    suppressing partially corrupted textbook text.

    quality=1.0 -> weight 1.00
    quality=0.5 -> weight 0.90
    quality=0.0 -> weight 0.80
    """

    bounded = max(
        0.0,
        min(
            1.0,
            quality_score,
        ),
    )

    return (
        0.80
        + (
            0.20
            * bounded
        )
    )


def calculate_final_score(
    *,
    semantic_score: float,
    quality_score: float,
    authority: str,
) -> float:
    authority_weight = (
        AUTHORITY_WEIGHTS.get(
            authority,
            0.90,
        )
    )

    return (
        semantic_score
        * quality_weight(
            quality_score
        )
        * authority_weight
    )


def build_qdrant_filter(
    *,
    domain: str | None,
    source_id: int | None,
) -> Filter | None:
    conditions = []

    if domain:
        conditions.append(
            FieldCondition(
                key="domain",
                match=MatchValue(
                    value=domain
                ),
            )
        )

    if source_id is not None:
        conditions.append(
            FieldCondition(
                key="source_id",
                match=MatchValue(
                    value=source_id
                ),
            )
        )

    if not conditions:
        return None

    return Filter(
        must=conditions
    )


async def retrieve_knowledge(
    *,
    database: Session,
    query: str,
    limit: int = DEFAULT_LIMIT,
    domain: str | None = None,
    source_id: int | None = None,
) -> list[RetrievalResult]:
    clean_query = query.strip()

    if not clean_query:
        raise KnowledgeRetrievalError(
            "Retrieval query cannot be empty."
        )

    limit = max(
        1,
        min(
            limit,
            MAX_LIMIT,
        ),
    )

    try:
        ensure_collection()

        embeddings = await embed_texts(
            [
                clean_query
            ]
        )

    except (
        KnowledgeEmbeddingError,
        KnowledgeVectorStoreError,
    ) as exc:
        raise KnowledgeRetrievalError(
            str(exc)
        ) from exc

    query_vector = embeddings[0]

    candidate_limit = min(
        max(
            limit
            * CANDIDATE_MULTIPLIER,
            limit,
        ),
        100,
    )

    query_filter = build_qdrant_filter(
        domain=domain,
        source_id=source_id,
    )

    client = get_qdrant_client()

    try:
        response = client.query_points(
            collection_name=(
                COLLECTION_NAME
            ),

            query=query_vector,

            query_filter=query_filter,

            limit=candidate_limit,

            with_payload=True,

            with_vectors=False,
        )

    except Exception as exc:
        raise KnowledgeRetrievalError(
            f"Qdrant search failed: {exc}"
        ) from exc

    scored_points = (
        response.points
    )

    results = []

    for point in scored_points:
        payload = (
            point.payload
            or {}
        )

        chunk_id = payload.get(
            "chunk_id"
        )

        if chunk_id is None:
            continue

        chunk = database.get(
            KnowledgeChunk,
            int(chunk_id),
        )

        if chunk is None:
            continue

        if not chunk.retrieval_enabled:
            continue

        source = database.get(
            KnowledgeSource,
            chunk.source_id,
        )

        if source is None:
            continue

        # Disabled sources must never participate
        # in normal retrieval.
        if not source.enabled:
            continue

        # Only fully indexed sources should be
        # considered authoritative retrieval data.
        if source.status != "ready":
            continue

        semantic_score = float(
            point.score
        )

        authority_weight = (
            AUTHORITY_WEIGHTS.get(
                source.authority,
                0.90,
            )
        )

        final_score = (
            calculate_final_score(
                semantic_score=(
                    semantic_score
                ),

                quality_score=(
                    chunk.quality_score
                ),

                authority=(
                    source.authority
                ),
            )
        )

        results.append(
            RetrievalResult(
                chunk_id=chunk.id,

                chunk_index=(
                    chunk.chunk_index
                ),

                source_id=(
                    source.id
                ),

                source_title=(
                    source.title
                ),

                domain=(
                    source.domain
                ),

                source_type=(
                    source.source_type
                ),

                authority=(
                    source.authority
                ),

                edition=(
                    source.edition
                ),

                page_start=(
                    chunk.page_start
                ),

                page_end=(
                    chunk.page_end
                ),

                section_hint=(
                    chunk.section_hint
                ),

                text=chunk.text,

                semantic_score=(
                    semantic_score
                ),

                quality_score=(
                    chunk.quality_score
                ),

                authority_weight=(
                    authority_weight
                ),

                final_score=(
                    final_score
                ),
            )
        )

    results.sort(
        key=lambda item:
            item.final_score,
        reverse=True,
    )

    return results[:limit]