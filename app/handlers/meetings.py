from aiogram import F, Router
from aiogram.types import CallbackQuery
from app.services.meetings import MeetingService
from app.services.users import UserService
from app.keyboards import meeting_decision_keyboard, precheck_keyboard, attendance_keyboard

router = Router()

# Сервисы
meeting_service = MeetingService("dating.db", meeting_price_stars=10)
user_service = UserService("dating.db", default_stars_balance=100)

@router.callback_query(F.data.startswith("confirm_meeting:"))
async def confirm_meeting(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":")[1])
    me = await user_service.get_by_tg_id(callback.from_user.id)
    ok, text = await meeting_service.confirm_meeting(match_id, me["id"])
    await callback.answer(text, show_alert=not ok)

    if ok:
        users = await meeting_service.users_for_match(match_id)
        match = await meeting_service.get_match(match_id)
        if users and match and match["status"] == "confirmed":
            for user in users:
                await callback.bot.send_message(
                    user["tg_id"],
                    (
                        "✅ Оба подтвердили встречу!\n"
                        f"Место: {match['meetup_place']}\n"
                        f"Время: {match['meetup_time'][:16].replace('T', ' ')}"
                    ),
                    reply_markup=attendance_keyboard(match_id)
                )

@router.callback_query(F.data.startswith("reject_meeting:"))
async def reject_meeting(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":")[1])
    me = await user_service.get_by_tg_id(callback.from_user.id)
    ok = await meeting_service.reject_meeting(match_id, me["id"])
    if not ok:
        await callback.answer("Нельзя отклонить", show_alert=True)
        return
    users = await meeting_service.users_for_match(match_id)
    if users:
        for user in users:
            await callback.bot.send_message(user["tg_id"], "❌ Встреча отменена одним из участников.")
    await callback.answer("Встреча отклонена")

@router.callback_query(F.data.startswith("precheck_yes:"))
async def precheck_yes(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":")[1])
    me = await user_service.get_by_tg_id(callback.from_user.id)
    await meeting_service.store_precheck(match_id, me["id"], True)
    await callback.answer("Отлично, ждём встречу!")

@router.callback_query(F.data.startswith("precheck_no:"))
async def precheck_no(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":")[1])
    me = await user_service.get_by_tg_id(callback.from_user.id)
    await meeting_service.store_precheck(match_id, me["id"], False)
    users = await meeting_service.users_for_match(match_id)
    if users:
        for user in users:
            await callback.bot.send_message(user["tg_id"], "❌ Встреча отменена после pre-check.")
    await callback.answer("Встреча отменена")

@router.callback_query(F.data.startswith("came_yes:"))
async def came_yes(callback: CallbackQuery) -> None:
    await _store_feedback(callback, True)

@router.callback_query(F.data.startswith("came_no:"))
async def came_no(callback: CallbackQuery) -> None:
    await _store_feedback(callback, False)

async def _store_feedback(callback: CallbackQuery, came: bool) -> None:
    match_id = int(callback.data.split(":")[1])
    me = await user_service.get_by_tg_id(callback.from_user.id)
    ok = await meeting_service.save_feedback(match_id, me["id"], came)
    if not ok:
        await callback.answer("Не удалось сохранить ответ", show_alert=True)
        return
    await callback.answer("Ответ сохранён")