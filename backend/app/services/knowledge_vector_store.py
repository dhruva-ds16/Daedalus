from qdrant_client import QdrantClient

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)


QDRANT_URL = (
    "http://127.0.0.1:6333"
)

COLLECTION_NAME = (
    "daedalus_knowledge"
)

VECTOR_SIZE = 768


class KnowledgeVectorStoreError(
    Exception
):
    pass


def get_qdrant_client(
) -> QdrantClient:
    return QdrantClient(
        url=QDRANT_URL
    )


def ensure_collection() -> None:
    client = get_qdrant_client()

    try:
        collections = (
            client.get_collections()
        )

        names = {
            collection.name
            for collection
            in collections.collections
        }

        if COLLECTION_NAME in names:
            collection = (
                client.get_collection(
                    COLLECTION_NAME
                )
            )

            configured_size = (
                collection
                .config
                .params
                .vectors
                .size
            )

            if (
                configured_size
                != VECTOR_SIZE
            ):
                raise KnowledgeVectorStoreError(
                    "Existing Qdrant collection "
                    "uses a different vector size."
                )

            return

        client.create_collection(
            collection_name=(
                COLLECTION_NAME
            ),

            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )

    except KnowledgeVectorStoreError:
        raise

    except Exception as exc:
        raise KnowledgeVectorStoreError(
            f"Unable to initialize "
            f"Qdrant: {exc}"
        ) from exc


def upsert_points(
    points: list[PointStruct],
) -> None:
    if not points:
        return

    client = get_qdrant_client()

    try:
        client.upsert(
            collection_name=(
                COLLECTION_NAME
            ),
            points=points,
            wait=True,
        )

    except Exception as exc:
        raise KnowledgeVectorStoreError(
            f"Unable to write vectors "
            f"to Qdrant: {exc}"
        ) from exc


def delete_source_vectors(
    source_id: int,
) -> None:
    client = get_qdrant_client()

    try:
        ensure_collection()

        client.delete(
            collection_name=(
                COLLECTION_NAME
            ),

            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source_id",

                        match=MatchValue(
                            value=source_id
                        ),
                    )
                ]
            ),

            wait=True,
        )

    except Exception as exc:
        raise KnowledgeVectorStoreError(
            f"Unable to remove source "
            f"vectors from Qdrant: {exc}"
        ) from exc


def count_source_vectors(
    source_id: int,
) -> int:
    client = get_qdrant_client()

    try:
        ensure_collection()

        result = client.count(
            collection_name=(
                COLLECTION_NAME
            ),

            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="source_id",

                        match=MatchValue(
                            value=source_id
                        ),
                    )
                ]
            ),

            exact=True,
        )

        return result.count

    except Exception as exc:
        raise KnowledgeVectorStoreError(
            f"Unable to count source "
            f"vectors: {exc}"
        ) from exc