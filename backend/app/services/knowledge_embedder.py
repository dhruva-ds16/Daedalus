import httpx


OLLAMA_URL = "http://127.0.0.1:11434"

EMBEDDING_MODEL = "nomic-embed-text"

EMBEDDING_DIMENSIONS = 768

EMBEDDING_BATCH_SIZE = 16


class KnowledgeEmbeddingError(Exception):
    pass


def build_embedding_text(
    *,
    source_title: str,
    domain: str,
    edition: str | None,
    section_hint: str | None,
    page_start: int,
    page_end: int,
    text: str,
) -> str:
    metadata = [
        f"Source: {source_title}",
        f"Domain: {domain}",
    ]

    if edition:
        metadata.append(
            f"Edition: {edition}"
        )

    if section_hint:
        metadata.append(
            f"Section: {section_hint}"
        )

    if page_start == page_end:
        metadata.append(
            f"PDF Page: {page_start}"
        )

    else:
        metadata.append(
            f"PDF Pages: "
            f"{page_start}-{page_end}"
        )

    return (
        "\n".join(metadata)
        + "\n\n"
        + text.strip()
    )


async def embed_texts(
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        return []

    payload = {
        "model": EMBEDDING_MODEL,
        "input": texts,
    }

    try:
        async with httpx.AsyncClient(
            timeout=300.0
        ) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/embed",
                json=payload,
            )

            response.raise_for_status()

    except httpx.HTTPError as exc:
        raise KnowledgeEmbeddingError(
            "Unable to communicate with "
            "the Ollama embedding service."
        ) from exc

    try:
        data = response.json()

    except ValueError as exc:
        raise KnowledgeEmbeddingError(
            "Ollama returned an invalid "
            "embedding response."
        ) from exc

    embeddings = data.get(
        "embeddings"
    )

    if not isinstance(
        embeddings,
        list,
    ):
        raise KnowledgeEmbeddingError(
            "Ollama embedding response "
            "did not contain embeddings."
        )

    if len(embeddings) != len(texts):
        raise KnowledgeEmbeddingError(
            "Ollama returned an unexpected "
            "number of embeddings."
        )

    for embedding in embeddings:
        if (
            not isinstance(
                embedding,
                list,
            )
            or len(embedding)
            != EMBEDDING_DIMENSIONS
        ):
            raise KnowledgeEmbeddingError(
                "Embedding dimensions do not "
                "match the configured model."
            )

    return embeddings