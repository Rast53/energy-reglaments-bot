from __future__ import annotations

import logging
import re

import pymupdf4llm

from indexer.models import Chunk

logger = logging.getLogger(__name__)

SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(\S.{0,80})", re.MULTILINE)

MIN_TOKENS = 50
MAX_TOKENS = 400


def _approx_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def _split_into_sections(md_text: str) -> list[tuple[str, str, str]]:
    """Split markdown text into (section_num, section_title, body) tuples."""
    matches = list(SECTION_RE.finditer(md_text))
    if not matches:
        return [("0", "Документ", md_text.strip())]

    sections: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        section_num = m.group(1)
        section_title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        body = md_text[start:end].strip()
        header = f"{section_num} {section_title}"
        full_text = f"{header}\n\n{body}" if body else header
        sections.append((section_num, section_title, full_text))

    return sections


def _merge_small_sections(
    sections: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Merge sections smaller than MIN_TOKENS with the next section."""
    if not sections:
        return sections

    merged: list[tuple[str, str, str]] = []
    carry: tuple[str, str, str] | None = None

    for section_num, section_title, text in sections:
        if carry is not None:
            combined_text = carry[2] + "\n\n" + text
            current = (carry[0], carry[1], combined_text)
        else:
            current = (section_num, section_title, text)

        if _approx_tokens(current[2]) < MIN_TOKENS:
            carry = current
        else:
            merged.append(current)
            carry = None

    if carry is not None:
        if merged:
            last = merged[-1]
            merged[-1] = (last[0], last[1], last[2] + "\n\n" + carry[2])
        else:
            merged.append(carry)

    return merged


def _split_large_section(
    section_num: str, section_title: str, text: str,
) -> list[tuple[str, str, str]]:
    """Split a section exceeding MAX_TOKENS into paragraph-based sub-chunks."""
    if _approx_tokens(text) <= MAX_TOKENS:
        return [(section_num, section_title, text)]

    paragraphs = re.split(r"\n\n+", text)
    sub_chunks: list[tuple[str, str, str]] = []
    current_parts: list[str] = []
    current_tokens = 0

    prefix = f"{section_num} {section_title}"

    for para in paragraphs:
        para_tokens = _approx_tokens(para)
        if current_tokens + para_tokens > MAX_TOKENS and current_parts:
            chunk_text = "\n\n".join(current_parts)
            if sub_chunks:
                chunk_text = f"[{prefix}]\n\n{chunk_text}"
            sub_chunks.append((section_num, section_title, chunk_text))
            current_parts = []
            current_tokens = 0

        current_parts.append(para)
        current_tokens += para_tokens

    if current_parts:
        chunk_text = "\n\n".join(current_parts)
        if sub_chunks:
            chunk_text = f"[{prefix}]\n\n{chunk_text}"
        sub_chunks.append((section_num, section_title, chunk_text))

    return sub_chunks


_JUNK_TITLES = {"подробнее", "скачать", "загрузить", "ссылка", ""}


def _clean_doc_title(raw_title: str, doc_id: str) -> str:
    """Return a meaningful title, falling back to doc_id for junk values."""
    stripped = raw_title.strip()
    if stripped.lower() in _JUNK_TITLES or len(stripped) < 3:
        return doc_id
    return stripped


def pdf_to_chunks(file_path: str, version_meta: dict) -> list[Chunk]:
    """Parse a PDF file into a list of Chunk objects."""
    logger.info("Parsing PDF: %s", file_path)
    md_text: str = pymupdf4llm.to_markdown(file_path)

    sections = _split_into_sections(md_text)
    sections = _merge_small_sections(sections)

    all_sub_chunks: list[tuple[str, str, str]] = []
    for section_num, section_title, text in sections:
        all_sub_chunks.extend(
            _split_large_section(section_num, section_title, text)
        )

    doc_id = version_meta["doc_id"]
    version_date = str(version_meta["valid_from"])
    doc_title = _clean_doc_title(version_meta.get("doc_title", ""), doc_id)
    is_changes = "изменени" in doc_title.lower()

    chunks: list[Chunk] = []
    for idx, (section_num, section_title, text) in enumerate(all_sub_chunks):
        chunk = Chunk(
            doc_id=doc_id,
            doc_title=doc_title,
            appendix_num=version_meta.get("appendix_num"),
            version_id=version_date,
            valid_from=version_date,
            valid_until=(
                str(version_meta["valid_until"])
                if version_meta.get("valid_until")
                else None
            ),
            status=version_meta.get("status", "current"),
            is_current=version_meta.get("status") == "current",
            is_changes_table=is_changes,
            section=section_num,
            section_title=section_title,
            text=text,
            chunk_index=idx,
            source_url=version_meta.get("source_url", ""),
            file_hash=version_meta.get("file_hash", ""),
        )
        chunks.append(chunk)

    logger.info("Created %d chunks from %s", len(chunks), file_path)
    return chunks
