from aiogram import F, Router
from aiogram.types import Message

from app.keyboards import (
    ATTENDANCE_NO,
    ATTENDANCE_YES,
    CALL_ACCEPT,
    CALL_REJECT,
    CALL_REQUEST,
    MEETING_CONFIRM,
    MEETING_REJECT,
    PRECHECK_NO,
    PRECHECK_YES,
    attendance_keyboard,
    call_request_keyboard,
    call_response_keyboard,
    main_menu_keyboard,
    meeting_decision_keyboard,
)

router = Router()


@router.message(F.text == CALL_REQUEST)
async def request_call(message: Message) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    match = await message.bot.meeting_service.pending_call_match_for_user(me["id"])
    if not match:
        await message.answer("Сейчас нет взаимного лайка для звонка.")
        return

    ok, text = await message.bot.meeting_service.request_call(match["id"], me["id"])
    await message.answer(text)
    if not ok:
        return

    users = await message.bot.meeting_service.users_for_match(match["id"])
    if not users:
        return
    for user in users:
        if user["id"] == me["id"]:
            continue
        await message.bot.send_message(
            user["tg_id"],
            "Тебе отправили запрос на совместный звонок 📞",
            reply_markup=call_response_keyboard(),
        )


@router.message(F.text == CALL_ACCEPT)
async def accept_call(message: Message) -> None:
    await _respond_call(message, accepted=True)


@router.message(F.text == CALL_REJECT)
async def reject_call(message: Message) -> None:
    await _respond_call(message, accepted=False)


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


async def _respond_call(message: Message, accepted: bool) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    match = await message.bot.meeting_service.pending_call_match_for_user(me["id"])
    if not match:
        await message.answer("Сейчас нет активного запроса на звонок.")
        return

    ok, text = await message.bot.meeting_service.respond_call(match["id"], me["id"], accepted)
    await message.answer(text)
    if not ok:
        return

    users = await message.bot.meeting_service.users_for_match(match["id"])
    if not users:
        return

    match_fresh = await message.bot.meeting_service.get_match(match["id"])
    if not match_fresh:
        return

    if match_fresh["status"] == "pending_confirm":
        for user in users:
            await message.bot.send_message(
                user["tg_id"],
                "Звонок согласован ✅\nТеперь можно предложить офлайн-встречу.",
                reply_markup=meeting_decision_keyboard(),
            )
        return

    if match_fresh["status"] == "cancelled":
        for user in users:
            await message.bot.send_message(user["tg_id"], "❌ Запрос на звонок отклонён. Матч отменён.")


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
