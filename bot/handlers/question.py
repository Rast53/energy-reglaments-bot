from __future__ import annotations

import logging
import os

from aiogram import F, Router
from aiogram.types import Message
from qdrant_client import AsyncQdrantClient

from bot.services.openclaw import ask_openclaw
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
        logger.info("Question from user=%s, mode=%s", message.from_user.id, mode)

        api_key = os.environ["OPENROUTER_API_KEY"]
        embedding_model = os.environ.get("EMBEDDING_MODEL", "openai/text-embedding-3-large")
        openclaw_url = os.environ.get("OPENCLAW_URL", "http://openclaw:18789")
        openclaw_api_key = os.environ["OPENCLAW_API_KEY"]
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

        result = await ask_openclaw(
            question=text,
            formatted_context=formatted_context,
            url=openclaw_url,
            api_key=openclaw_api_key,
        )

        sources_valid = validate_sources(result.get("sources", []), chunks)
        if not sources_valid:
            result["confidence"] = "low"
            logger.warning("Source validation failed, confidence set to low")

        answer_text = format_answer(result)
        await message.answer(answer_text, parse_mode="HTML", disable_web_page_preview=True)

    except Exception:
        logger.exception("Error processing question from user=%s", message.from_user.id)
        await message.answer(
            "❌ Произошла ошибка при обработке вопроса. Попробуйте позже.",
            parse_mode="HTML",
        )
