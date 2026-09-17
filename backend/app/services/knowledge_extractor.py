import re

from pathlib import Path

import pymupdf

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database.models import KnowledgePage
from app.database.models import KnowledgeSource


class KnowledgeExtractionError(Exception):
    pass


def normalize_page_text(
    text: str,
) -> str:
    text = text.replace(
        "\x00",
        "",
    )

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    text = re.sub(
        r"[ \t]+\n",
        "\n",
        text,
    )

    text = re.sub(
        r"\n{4,}",
        "\n\n\n",
        text,
    )

    return text.strip()


def count_words(
    text: str,
) -> int:
    return len(
        re.findall(
            r"\S+",
            text,
        )
    )


def extract_knowledge_source(
    *,
    database: Session,
    source: KnowledgeSource,
) -> KnowledgeSource:
    file_path = Path(
        source.file_path
    )

    if not file_path.exists():
        raise KnowledgeExtractionError(
            "The source PDF no longer exists on disk."
        )

    if source.file_type != "pdf":
        raise KnowledgeExtractionError(
            "Only PDF extraction is currently supported."
        )

    source.status = "extracting"
    source.error_message = None

    database.commit()

    document = None

    try:
        document = pymupdf.open(
            str(file_path)
        )

        if document.needs_pass:
            raise KnowledgeExtractionError(
                "Password-protected PDFs are not supported."
            )

        page_count = (
            document.page_count
        )

        if page_count <= 0:
            raise KnowledgeExtractionError(
                "The PDF contains no pages."
            )

        database.execute(
            delete(
                KnowledgePage
            ).where(
                KnowledgePage.source_id
                == source.id
            )
        )

        database.flush()

        extracted_pages = []

        for page_index in range(
            page_count
        ):
            page = document.load_page(
                page_index
            )

            raw_text = page.get_text(
                "text"
            )

            text = normalize_page_text(
                raw_text
            )

            page_number = (
                page_index + 1
            )

            extracted_pages.append(
                KnowledgePage(
                    source_id=source.id,

                    page_number=(
                        page_number
                    ),

                    text=text,

                    character_count=len(
                        text
                    ),

                    word_count=count_words(
                        text
                    ),

                    has_text=bool(
                        text.strip()
                    ),
                )
            )

            if (
                len(extracted_pages)
                >= 100
            ):
                database.add_all(
                    extracted_pages
                )

                database.flush()

                extracted_pages = []

        if extracted_pages:
            database.add_all(
                extracted_pages
            )

            database.flush()

        source.page_count = (
            page_count
        )

        source.status = (
            "extracted"
        )

        source.error_message = None

        database.commit()

        database.refresh(
            source
        )

        return source

    except KnowledgeExtractionError as exc:
        database.rollback()

        source = database.get(
            KnowledgeSource,
            source.id,
        )

        if source is not None:
            source.status = "failed"

            source.error_message = str(
                exc
            )[:2000]

            database.commit()

        raise

    except Exception as exc:
        database.rollback()

        source = database.get(
            KnowledgeSource,
            source.id,
        )

        if source is not None:
            source.status = "failed"

            source.error_message = str(
                exc
            )[:2000]

            database.commit()

        raise KnowledgeExtractionError(
            f"PDF extraction failed: {exc}"
        ) from exc

    finally:
        if document is not None:
            document.close()