from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router(name="start")

WELCOME_TEXT = (
    "👋 Привет! Я бот по регламентам <b>ОРЭМ</b> "
    "(Оптовый рынок электроэнергии и мощности).\n\n"
    "Задайте мне вопрос по любому приложению к Договору о присоединении, "
    "и я найду ответ в актуальных редакциях документов.\n\n"
    "📝 <b>Примеры вопросов:</b>\n"
    "• Какие сроки подачи ценовых заявок на РСВ?\n"
    "• Что изменится в приложении 7 с 1 июля?\n"
    "• Порядок расчёта стоимости отклонений\n\n"
    "⚙️ <b>Команды:</b>\n"
    "/help — примеры вопросов\n"
    "/versions N — список редакций приложения N"
)

HELP_TEXT = (
    "📝 <b>Примеры вопросов:</b>\n\n"
    "• Какие сроки подачи ценовых заявок на РСВ?\n"
    "• Как рассчитывается стоимость отклонений?\n"
    "• Порядок определения состава ГТП генерации\n"
    "• Что изменится в приложении 7 с 1 июля?\n"
    "• Какие штрафные санкции за отклонение от плановых объёмов?\n\n"
    "💡 Просто напишите свой вопрос текстом, и я найду ответ "
    "в актуальных документах на np-sr.ru."
)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")
