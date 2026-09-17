import hashlib
import re

from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import KnowledgeChunk
from app.database.models import KnowledgePage
from app.database.models import KnowledgeSource


TARGET_WORDS = 450
MAX_WORDS = 650
MIN_WORDS = 80
OVERLAP_WORDS = 70


class KnowledgeChunkingError(Exception):
    pass


@dataclass
class PageAnalysis:
    page_number: int
    content_type: str
    quality_score: float
    retrieval_enabled: bool
    section_hint: str | None


def count_words(
    text: str,
) -> int:
    return len(
        re.findall(
            r"\S+",
            text,
        )
    )


def text_hash(
    text: str,
) -> str:
    return hashlib.sha256(
        text.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()


def control_character_ratio(
    text: str,
) -> float:
    if not text:
        return 0.0

    suspicious = 0

    for character in text:
        code = ord(character)

        if (
            code < 32
            and character
            not in "\n\t"
        ):
            suspicious += 1

    return suspicious / len(text)


def dotted_leader_ratio(
    text: str,
) -> float:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return 0.0

    matches = 0

    for line in lines:
        if re.search(
            r"\.{4,}\s*\d+\s*$",
            line,
        ):
            matches += 1

    return matches / len(lines)


def page_reference_ratio(
    text: str,
) -> float:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return 0.0

    matches = 0

    for line in lines:
        if re.search(
            r"(?:,\s*)?\d+(?:\s*,\s*\d+){1,}\s*$",
            line,
        ):
            matches += 1

    return matches / len(lines)


def detect_section_hint(
    text: str,
) -> str | None:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines[:12]:
        words = line.split()

        if not (
            1 <= len(words) <= 12
        ):
            continue

        if len(line) > 120:
            continue

        if re.fullmatch(
            r"\d+",
            line,
        ):
            continue

        if re.search(
            r"\.{4,}",
            line,
        ):
            continue

        alpha = sum(
            character.isalpha()
            for character in line
        )

        if alpha < 4:
            continue

        return line

    return None


def analyze_page(
    page: KnowledgePage,
    total_pages: int,
) -> PageAnalysis:
    text = page.text.strip()

    if not text:
        return PageAnalysis(
            page_number=page.page_number,
            content_type="low_text",
            quality_score=0.0,
            retrieval_enabled=False,
            section_hint=None,
        )

    word_count = page.word_count

    if word_count < 20:
        return PageAnalysis(
            page_number=page.page_number,
            content_type="low_text",
            quality_score=0.4,
            retrieval_enabled=False,
            section_hint=detect_section_hint(
                text
            ),
        )

    controls = (
        control_character_ratio(
            text
        )
    )

    quality_score = max(
        0.0,
        min(
            1.0,
            1.0 - (
                controls * 20.0
            ),
        ),
    )

    dotted = dotted_leader_ratio(
        text
    )

    if dotted >= 0.20:
        return PageAnalysis(
            page_number=page.page_number,
            content_type="toc",
            quality_score=quality_score,
            retrieval_enabled=False,
            section_hint="Table of Contents",
        )

    references = (
        page_reference_ratio(
            text
        )
    )

    if (
        page.page_number
        > total_pages * 0.80
        and references >= 0.20
    ):
        return PageAnalysis(
            page_number=page.page_number,
            content_type="index",
            quality_score=quality_score,
            retrieval_enabled=False,
            section_hint="Index",
        )

    if (
        page.page_number <= 15
        and word_count < 350
    ):
        return PageAnalysis(
            page_number=page.page_number,
            content_type="front_matter",
            quality_score=quality_score,
            retrieval_enabled=False,
            section_hint=detect_section_hint(
                text
            ),
        )

    return PageAnalysis(
        page_number=page.page_number,
        content_type="content",
        quality_score=quality_score,
        retrieval_enabled=True,
        section_hint=detect_section_hint(
            text
        ),
    )


def split_paragraphs(
    text: str,
) -> list[str]:
    blocks = re.split(
        r"\n\s*\n",
        text,
    )

    paragraphs = []

    for block in blocks:
        cleaned = re.sub(
            r"[ \t]+",
            " ",
            block,
        ).strip()

        if cleaned:
            paragraphs.append(
                cleaned
            )

    if len(paragraphs) <= 1:
        paragraphs = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

    return paragraphs


def split_large_paragraph(
    paragraph: str,
) -> list[str]:
    words = paragraph.split()

    if len(words) <= MAX_WORDS:
        return [paragraph]

    pieces = []

    start = 0

    while start < len(words):
        end = min(
            start + TARGET_WORDS,
            len(words),
        )

        pieces.append(
            " ".join(
                words[start:end]
            )
        )

        if end >= len(words):
            break

        start = max(
            end - OVERLAP_WORDS,
            start + 1,
        )

    return pieces


def build_page_chunks(
    page: KnowledgePage,
    analysis: PageAnalysis,
) -> list[dict]:
    paragraphs = []

    for paragraph in split_paragraphs(
        page.text
    ):
        paragraphs.extend(
            split_large_paragraph(
                paragraph
            )
        )

    chunks = []

    current = []
    current_words = 0

    for paragraph in paragraphs:
        paragraph_words = (
            count_words(
                paragraph
            )
        )

        if (
            current
            and current_words
            + paragraph_words
            > MAX_WORDS
        ):
            text = "\n\n".join(
                current
            )

            chunks.append(
                {
                    "text": text,
                    "page_start":
                        page.page_number,
                    "page_end":
                        page.page_number,
                    "content_type":
                        analysis.content_type,
                    "quality_score":
                        analysis.quality_score,
                    "retrieval_enabled":
                        analysis.retrieval_enabled,
                    "section_hint":
                        analysis.section_hint,
                }
            )

            overlap_words = (
                text.split()[
                    -OVERLAP_WORDS:
                ]
            )

            current = []

            if overlap_words:
                current.append(
                    " ".join(
                        overlap_words
                    )
                )

            current_words = len(
                overlap_words
            )

        current.append(
            paragraph
        )

        current_words += (
            paragraph_words
        )

        if (
            current_words
            >= TARGET_WORDS
        ):
            text = "\n\n".join(
                current
            )

            chunks.append(
                {
                    "text": text,
                    "page_start":
                        page.page_number,
                    "page_end":
                        page.page_number,
                    "content_type":
                        analysis.content_type,
                    "quality_score":
                        analysis.quality_score,
                    "retrieval_enabled":
                        analysis.retrieval_enabled,
                    "section_hint":
                        analysis.section_hint,
                }
            )

            overlap_words = (
                text.split()[
                    -OVERLAP_WORDS:
                ]
            )

            current = []

            if overlap_words:
                current.append(
                    " ".join(
                        overlap_words
                    )
                )

            current_words = len(
                overlap_words
            )

    if current:
        text = "\n\n".join(
            current
        )

        if (
            count_words(text)
            >= MIN_WORDS
            or not chunks
        ):
            chunks.append(
                {
                    "text": text,
                    "page_start":
                        page.page_number,
                    "page_end":
                        page.page_number,
                    "content_type":
                        analysis.content_type,
                    "quality_score":
                        analysis.quality_score,
                    "retrieval_enabled":
                        analysis.retrieval_enabled,
                    "section_hint":
                        analysis.section_hint,
                }
            )

        elif chunks:
            chunks[-1]["text"] += (
                "\n\n" + text
            )

    return chunks


def chunk_knowledge_source(
    *,
    database: Session,
    source: KnowledgeSource,
) -> KnowledgeSource:
    if source.page_count is None:
        raise KnowledgeChunkingError(
            "Source must be extracted before chunking."
        )

    source.status = "chunking"
    source.error_message = None

    database.commit()

    try:
        statement = (
            select(KnowledgePage)
            .where(
                KnowledgePage.source_id
                == source.id
            )
            .order_by(
                KnowledgePage.page_number
            )
        )

        pages = database.scalars(
            statement
        ).all()

        if not pages:
            raise KnowledgeChunkingError(
                "No extracted pages were found."
            )

        database.execute(
            delete(
                KnowledgeChunk
            ).where(
                KnowledgeChunk.source_id
                == source.id
            )
        )

        database.flush()

        chunk_index = 1

        pending = []

        for page in pages:
            analysis = analyze_page(
                page,
                len(pages),
            )

            page_chunks = (
                build_page_chunks(
                    page,
                    analysis,
                )
            )

            for item in page_chunks:
                chunk_text = (
                    item["text"].strip()
                )

                if not chunk_text:
                    continue

                pending.append(
                    KnowledgeChunk(
                        source_id=source.id,

                        chunk_index=(
                            chunk_index
                        ),

                        page_start=(
                            item[
                                "page_start"
                            ]
                        ),

                        page_end=(
                            item[
                                "page_end"
                            ]
                        ),

                        content_type=(
                            item[
                                "content_type"
                            ]
                        ),

                        section_hint=(
                            item[
                                "section_hint"
                            ]
                        ),

                        text=chunk_text,

                        character_count=len(
                            chunk_text
                        ),

                        word_count=(
                            count_words(
                                chunk_text
                            )
                        ),

                        quality_score=(
                            item[
                                "quality_score"
                            ]
                        ),

                        retrieval_enabled=(
                            item[
                                "retrieval_enabled"
                            ]
                        ),

                        text_hash=(
                            text_hash(
                                chunk_text
                            )
                        ),

                        vector_id=None,
                    )
                )

                chunk_index += 1

                if len(pending) >= 100:
                    database.add_all(
                        pending
                    )

                    database.flush()

                    pending = []

        if pending:
            database.add_all(
                pending
            )

            database.flush()

        source.chunk_count = (
            chunk_index - 1
        )

        source.status = "chunked"

        source.error_message = None

        database.commit()

        database.refresh(
            source
        )

        return source

    except KnowledgeChunkingError as exc:
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

        raise

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

        raise KnowledgeChunkingError(
            f"Chunking failed: {exc}"
        ) from exc