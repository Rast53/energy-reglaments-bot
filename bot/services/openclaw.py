from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
Ты эксперт по регламентам ОРЭМ (Оптовый рынок электроэнергии и мощности).
Отвечай ТОЛЬКО на основе предоставленных выдержек. Не придумывай информацию.
Всегда указывай: название документа, редакция от [дата], пункт [N].

[CONTEXT]
{context}

Верни ответ строго в JSON (без markdown-оборачивания):
{{
  "answer": "текст ответа",
  "sources": [{{"doc_title": "...", "version_date": "...", "section": "...", "status": "current"}}],
  "confidence": "high|medium|low",
  "has_future_changes": false,
  "future_changes_summary": ""
}}\
"""

DEFAULT_RESULT: dict[str, Any] = {
    "answer": "",
    "sources": [],
    "confidence": "low",
    "has_future_changes": False,
    "future_changes_summary": "",
}


async def ask_openclaw(
    question: str,
    formatted_context: str,
    url: str,
    api_key: str,
) -> dict[str, Any]:
    """Send question with context to OpenClaw and parse JSON response."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=formatted_context)

    payload = {
        "model": "gemini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_response(content)

    except httpx.HTTPStatusError as exc:
        logger.error("OpenClaw HTTP error: %s %s", exc.response.status_code, exc.response.text)
        return {**DEFAULT_RESULT, "answer": "Ошибка при обращении к LLM. Попробуйте позже."}

    except Exception:
        logger.exception("OpenClaw request failed")
        return {**DEFAULT_RESULT, "answer": "Ошибка при обращении к LLM. Попробуйте позже."}


def _parse_response(content: str) -> dict[str, Any]:
    """Parse JSON from LLM response, with fallback for non-JSON output."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        result = json.loads(cleaned)
        for key, default_val in DEFAULT_RESULT.items():
            if key not in result:
                result[key] = default_val
        return result
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from OpenClaw, using raw text as answer")
        return {**DEFAULT_RESULT, "answer": content.strip(), "confidence": "low"}
