from __future__ import annotations

import logging
import os

from aiogram import F, Router
from aiogram.types import Message
from qdrant_client import AsyncQdrantClient

from bot.services.openclaw import ask_llm
from bot.services.search import embed_text, search_qdrant
from bot.services.validator import detect_mode, validate_sources
from bot.utils.formatting import format_answer, format_chunks_for_prompt

logger = logging.getLogger(__name__)
router = Router(name="question")


@router.message(F.text)
async def handle_question(message: Message, qdrant: AsyncQdrantClient) -> None:
    """Main handler: text question → RAG pipeline → formatted answer."""
    text = message.text
    if not text or text.startswith("/"):
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        mode = detect_mode(text)
        username = message.from_user.username or str(message.from_user.id)
        logger.info("Question from user=%s username=%s mode=%s", message.from_user.id, username, mode)

        api_key = os.environ["OPENROUTER_API_KEY"]
        embedding_model = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
        llm_model = os.environ.get("LLM_MODEL", "google/gemini-2.0-flash-001")
        collection = os.environ.get("QDRANT_COLLECTION", "reglaments")

        vector = await embed_text(text, api_key=api_key, model=embedding_model)

        chunks = await search_qdrant(
            vector=vector,
            mode=mode,
            client=qdrant,
            collection=collection,
        )

        if not chunks:
            await message.answer(
                "🔍 К сожалению, не удалось найти релевантные документы. "
                "Попробуйте переформулировать вопрос.",
                parse_mode="HTML",
            )
            return

        formatted_context = format_chunks_for_prompt(chunks)

        result = await ask_llm(
            question=text,
            formatted_context=formatted_context,
            api_key=api_key,
            model=llm_model,
        )

        sources_valid = validate_sources(result.get("sources", []), chunks)
        if not sources_valid:
            result["confidence"] = "low"
            logger.warning("Source validation failed, confidence set to low")

        answer_text = format_answer(result)
        await message.answer(answer_text, parse_mode="HTML", disable_web_page_preview=True)

    except Exception:
        username = message.from_user.username or str(message.from_user.id)
        logger.exception("Error processing question from user=%s username=%s", message.from_user.id, username)
        await message.answer(
            "❌ Произошла ошибка при обработке вопроса. Попробуйте позже.",
            parse_mode="HTML",
        )
