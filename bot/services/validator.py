from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

FUTURE_KEYWORDS = [
    "будущ",
    "изменени",
    "вступ",
    "с 1",
    "с 01",
    "планируется",
    "предстоящ",
    "новая редакция",
    "когда изменится",
    "что изменится",
    "следующ редакц",
]

CURRENT_KEYWORDS = [
    "текущ",
    "действующ",
    "сейчас",
    "настоящ",
]


def detect_mode(text: str) -> str:
    """Determine query mode: 'current', 'future', or 'both'."""
    text_lower = text.lower()
    has_future = any(kw in text_lower for kw in FUTURE_KEYWORDS)
    has_current = any(kw in text_lower for kw in CURRENT_KEYWORDS)

    if has_future and has_current:
        return "both"
    if has_future:
        return "future"
    return "current"


def validate_sources(
    sources: list[dict[str, Any]],
    chunks: list[Any],
) -> bool:
    """Check that every LLM-reported source is traceable to retrieved chunks.

    Returns True if all sources are valid, False otherwise.
    """
    if not sources:
        return True

    for source in sources:
        source_doc_id = source.get("doc_title", "")
        source_section = source.get("section", "")
        found = any(
            _payload(chunk).get("doc_title") == source_doc_id
            and _payload(chunk).get("section") == source_section
            for chunk in chunks
        )
        if not found:
            logger.warning(
                "Source not found in chunks: doc_title=%s section=%s",
                source_doc_id,
                source_section,
            )
            return False

    return True


def _payload(chunk: Any) -> dict[str, Any]:
    """Extract payload dict from a Qdrant ScoredPoint or plain dict."""
    if hasattr(chunk, "payload"):
        return chunk.payload or {}
    if isinstance(chunk, dict):
        return chunk.get("payload", chunk)
    return {}
