from __future__ import annotations

import html
import logging
import os

import asyncpg
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router(name="versions")

STATUS_EMOJI = {
    "current": "🟢",
    "future": "🔵",
    "archive": "⚪",
}


@router.message(Command("versions"))
async def cmd_versions(message: Message, command: CommandObject) -> None:
    """Show document versions for a given appendix number."""
    appendix_num = (command.args or "").strip()

    if not appendix_num:
        await message.answer(
            "ℹ️ Укажите номер приложения.\n"
            "Пример: <code>/versions 7</code>",
            parse_mode="HTML",
        )
        return

    try:
        database_url = os.environ["DATABASE_URL"]
        conn = await asyncpg.connect(database_url)

        try:
            rows = await conn.fetch(
                """
                SELECT d.title, dv.version_date, dv.status,
                       dv.valid_from, dv.valid_until
                FROM document_versions dv
                JOIN documents d ON d.doc_id = dv.doc_id
                WHERE d.appendix_num = $1
                ORDER BY dv.valid_from DESC
                """,
                appendix_num,
            )
        finally:
            await conn.close()

        if not rows:
            await message.answer(
                f"🔍 Не найдено версий для приложения <b>{html.escape(appendix_num)}</b>.",
                parse_mode="HTML",
            )
            return

        title = html.escape(str(rows[0]["title"]))
        lines = [f"📄 <b>{title}</b>\n"]

        for row in rows:
            emoji = STATUS_EMOJI.get(row["status"], "⚪")
            status = row["status"]
            valid_from = row["valid_from"].strftime("%d.%m.%Y") if row["valid_from"] else "—"
            valid_until = row["valid_until"].strftime("%d.%m.%Y") if row["valid_until"] else "—"
            version_date = (
                row["version_date"].strftime("%d.%m.%Y") if row["version_date"] else "—"
            )

            line = f"{emoji} ред. {version_date} | {status} | {valid_from} – {valid_until}"
            lines.append(line)

        await message.answer("\n".join(lines), parse_mode="HTML")

    except Exception:
        logger.exception("Error fetching versions for appendix=%s", appendix_num)
        await message.answer(
            "❌ Ошибка при получении данных. Попробуйте позже.",
            parse_mode="HTML",
        )
