from aiogram import F, Router
from aiogram.types import Message

from app.keyboards import (
    ATTENDANCE_NO,
    ATTENDANCE_YES,
    MEETING_CONFIRM,
    MEETING_REJECT,
    PRECHECK_NO,
    PRECHECK_YES,
    attendance_keyboard,
    main_menu_keyboard,
)

router = Router()


@router.message(F.text == MEETING_CONFIRM)
async def confirm_meeting(message: Message) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    match = await message.bot.meeting_service.pending_match_for_user(me["id"])
    if not match:
        await message.answer("Нет встречи, ожидающей подтверждения.", reply_markup=main_menu_keyboard(profile_enabled=True))
        return

    ok, text = await message.bot.meeting_service.confirm_meeting(match["id"], me["id"])
    await message.answer(text)

    if ok:
        users = await message.bot.meeting_service.users_for_match(match["id"])
        match_fresh = await message.bot.meeting_service.get_match(match["id"])
        if users and match_fresh and match_fresh["status"] == "confirmed":
            for user in users:
                await message.bot.send_message(
                    user["tg_id"],
                    (
                        "✅ Оба подтвердили встречу!\n"
                        f"Место: {match_fresh['meetup_place']}\n"
                        f"Время: {match_fresh['meetup_time'][:16].replace('T', ' ')}"
                    ),
                    reply_markup=attendance_keyboard(),
                )


@router.message(F.text == MEETING_REJECT)
async def reject_meeting(message: Message) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    match = await message.bot.meeting_service.pending_match_for_user(me["id"])
    if not match:
        await message.answer("Нет встречи для отмены.")
        return

    ok = await message.bot.meeting_service.reject_meeting(match["id"], me["id"])
    if not ok:
        await message.answer("Нельзя отклонить встречу.")
        return

    users = await message.bot.meeting_service.users_for_match(match["id"])
    if users:
        for user in users:
            await message.bot.send_message(user["tg_id"], "❌ Встреча отменена одним из участников.")


@router.message(F.text == PRECHECK_YES)
async def precheck_yes(message: Message) -> None:
    await _store_precheck(message, True)


@router.message(F.text == PRECHECK_NO)
async def precheck_no(message: Message) -> None:
    await _store_precheck(message, False)


@router.message(F.text == ATTENDANCE_YES)
async def came_yes(message: Message) -> None:
    await _store_feedback(message, True)


@router.message(F.text == ATTENDANCE_NO)
async def came_no(message: Message) -> None:
    await _store_feedback(message, False)


async def _store_precheck(message: Message, going: bool) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    match = await message.bot.meeting_service.precheck_match_for_user(me["id"])
    if not match:
        await message.answer("Сейчас нет встречи, где нужен pre-check.")
        return

    await message.bot.meeting_service.store_precheck(match["id"], me["id"], going)
    if going:
        await message.answer("Отлично, ждём встречу! 💫")
        return

    users = await message.bot.meeting_service.users_for_match(match["id"])
    if users:
        for user in users:
            await message.bot.send_message(user["tg_id"], "❌ Встреча отменена после pre-check.")


async def _store_feedback(message: Message, came: bool) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    match = await message.bot.meeting_service.feedback_match_for_user(me["id"])
    if not match:
        await message.answer("Сейчас нет встречи, где нужен отзыв.")
        return

    ok = await message.bot.meeting_service.save_feedback(match["id"], me["id"], came)
    await message.answer("Ответ сохранён ✅" if ok else "Не удалось сохранить ответ")
