from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from qdrant_client import AsyncQdrantClient

from bot.handlers import question, start, versions

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot_token = os.environ["BOT_TOKEN"]
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")

    qdrant = AsyncQdrantClient(url=qdrant_url)
    logger.info("Qdrant client initialized: %s", qdrant_url)

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp["qdrant"] = qdrant

    dp.include_router(start.router)
    dp.include_router(versions.router)
    dp.include_router(question.router)

    logger.info("Bot starting polling...")
    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        await qdrant.close()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
