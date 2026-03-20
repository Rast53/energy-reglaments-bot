from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import web
from qdrant_client import AsyncQdrantClient

from bot.handlers import question, start, versions

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def run_health_server() -> None:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Health server started on :8080")


async def main() -> None:
    bot_token = os.environ["BOT_TOKEN"]
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")

    qdrant = AsyncQdrantClient(url=qdrant_url)
    logger.info("Qdrant client initialized: %s", qdrant_url)

    proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    if proxy_url:
        logger.info("Using proxy: %s", proxy_url.split("@")[-1])
        bot = Bot(token=bot_token, session=AiohttpSession(proxy=proxy_url))
    else:
        bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp["qdrant"] = qdrant

    dp.include_router(start.router)
    dp.include_router(versions.router)
    dp.include_router(question.router)

    await run_health_server()

    logger.info("Bot starting polling...")
    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        await qdrant.close()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
