import asyncio
import logging

from aiogram import Bot

from app.keyboards import attendance_keyboard, precheck_keyboard
from app.services.meetings import MeetingService

logger = logging.getLogger(__name__)


async def scheduler_loop(bot: Bot, meeting_service: MeetingService) -> None:
    while True:
        try:
            expired_ids = await meeting_service.pending_confirm_expired()
            for match_id in expired_ids:
                users = await meeting_service.users_for_match(match_id)
                if users:
                    for user in users:
                        await bot.send_message(user["tg_id"], "⏰ 24 часа прошли. Матч удалён.")

            prechecks = await meeting_service.due_precheck()
            for match in prechecks:
                users = await meeting_service.users_for_match(match["id"])
                if not users:
                    continue
                for user in users:
                    await bot.send_message(
                        user["tg_id"],
                        "Напоминание за 2-3 часа: ты точно идёшь на встречу?",
                        reply_markup=precheck_keyboard(match["id"]),
                    )

            cancelled = await meeting_service.cancel_precheck_timeouts()
            for match_id in cancelled:
                users = await meeting_service.users_for_match(match_id)
                if users:
                    for user in users:
                        await bot.send_message(user["tg_id"], "Встреча отменена: не было подтверждения перед встречей.")

            feedback_due = await meeting_service.due_feedback()
            for match in feedback_due:
                users = await meeting_service.users_for_match(match["id"])
                if not users:
                    continue
                for user in users:
                    await bot.send_message(
                        user["tg_id"],
                        "Человек пришёл на встречу?",
                        reply_markup=attendance_keyboard(match["id"]),
                    )
        except Exception:  # noqa: BLE001
            logger.exception("Scheduler iteration failed")

        await asyncio.sleep(60)
