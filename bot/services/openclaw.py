from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

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


async def ask_llm(
    question: str,
    formatted_context: str,
    api_key: str,
    model: str = "google/gemini-2.0-flash-001",
) -> dict[str, Any]:
    """Send question with context to OpenRouter and parse JSON response."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=formatted_context)

    payload = {
        "model": model,
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
                OPENROUTER_CHAT_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_response(content)

    except httpx.HTTPStatusError as exc:
        logger.error("OpenRouter HTTP error: %s %s", exc.response.status_code, exc.response.text)
        return {**DEFAULT_RESULT, "answer": "Ошибка при обращении к LLM. Попробуйте позже."}

    except Exception:
        logger.exception("OpenRouter request failed")
        return {**DEFAULT_RESULT, "answer": "Ошибка при обращении к LLM. Попробуйте позже."}


def _parse_response(content: str) -> dict[str, Any]:
    """Parse JSON from LLM response with robust fallbacks."""
    cleaned = content.strip()

    # Strip markdown code block wrapper (```json ... ```)
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Try direct parse first
    try:
        result = json.loads(cleaned)
        return _ensure_keys(result)
    except json.JSONDecodeError:
        pass

    # Fallback: find JSON object boundaries
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(cleaned[start : end + 1])
            return _ensure_keys(result)
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse JSON from LLM, using raw text as answer")
    return {**DEFAULT_RESULT, "answer": content.strip(), "confidence": "low"}


def _ensure_keys(result: dict[str, Any]) -> dict[str, Any]:
    """Ensure all required keys exist in the result dict."""
    for key, default_val in DEFAULT_RESULT.items():
        if key not in result:
            result[key] = default_val
    return result
