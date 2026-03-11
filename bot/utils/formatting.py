from __future__ import annotations

import html
from typing import Any


def format_chunks_for_prompt(chunks: list[Any]) -> str:
    """Format Qdrant chunks into readable context for the LLM system prompt."""
    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        payload = _payload(chunk)
        doc_title = payload.get("doc_title", "—")
        section = payload.get("section", "—")
        section_title = payload.get("section_title", "")
        valid_from = payload.get("valid_from", "—")
        status = payload.get("status", "—")
        text = payload.get("text", "")

        header = (
            f"--- Источник {i} ---\n"
            f"Документ: {doc_title}\n"
            f"Редакция от: {valid_from} (статус: {status})\n"
            f"Пункт: {section}"
        )
        if section_title:
            header += f" — {section_title}"
        header += f"\n\n{text}"
        parts.append(header)

    return "\n\n".join(parts)


def format_answer(result: dict[str, Any]) -> str:
    """Format LLM result dict into Telegram HTML message."""
    answer = html.escape(result.get("answer", "Нет ответа"))
    confidence = result.get("confidence", "low")
    sources = result.get("sources", [])
    has_future = result.get("has_future_changes", False)
    future_summary = result.get("future_changes_summary", "")

    parts: list[str] = [f"📋 <b>Ответ</b>\n\n{answer}"]

    if sources:
        source_lines = []
        for s in sources:
            doc = html.escape(str(s.get("doc_title", "—")))
            ver = html.escape(str(s.get("version_date", "—")))
            sec = html.escape(str(s.get("section", "—")))
            source_lines.append(f"• {doc}, ред. {ver}, п. {sec}")
        parts.append("📌 <b>Источники:</b>\n" + "\n".join(source_lines))

    if has_future and future_summary:
        escaped_summary = html.escape(future_summary)
        parts.append(f"⏰ <b>Будущие изменения:</b>\n{escaped_summary}")

    if confidence == "low":
        parts.append(
            '⚠️ <i>Низкая уверенность. Рекомендую проверить на '
            '<a href="https://np-sr.ru">np-sr.ru</a></i>'
        )

    return "\n\n".join(parts)


def _payload(chunk: Any) -> dict[str, Any]:
    """Extract payload dict from a Qdrant ScoredPoint or plain dict."""
    if hasattr(chunk, "payload"):
        return chunk.payload or {}
    if isinstance(chunk, dict):
        return chunk.get("payload", chunk)
    return {}
