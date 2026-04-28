import re

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
    meeting_decision_keyboard,
)

router = Router()


@router.message(F.text.startswith("📞 Позвонить #"))
@router.message(F.text == CALL_REQUEST)
async def request_call(message: Message) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    selected_id = None
    found = re.search(r"#(\d+)$", (message.text or "").strip())
    if found:
        selected_id = int(found.group(1))

    if selected_id is None:
        match = await message.bot.meeting_service.pending_call_match_for_user(me["id"])
        if not match:
            await message.answer("Сейчас нет взаимного лайка для звонка.")
            return
        selected_id = match["id"]

    ok, text = await message.bot.meeting_service.request_call(selected_id, me["id"])
    await message.answer(text)
    if not ok:
        return

    users = await message.bot.meeting_service.users_for_match(selected_id)
    if users:
        for user in users:
            if user["id"] != me["id"]:
                await message.bot.send_message(user["tg_id"], "Тебе отправили запрос на звонок 📞")


@router.message(F.text == CALL_ACCEPT)
async def accept_call(message: Message) -> None:
    await _respond_call(message, accepted=True)


@router.message(F.text == CALL_REJECT)
async def reject_call(message: Message) -> None:
    await _respond_call(message, accepted=False)


@router.message(F.text == MEETING_CONFIRM)
async def confirm_partner(message: Message) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    match = await message.bot.meeting_service.pending_match_for_user(me["id"])
    if not match:
        await message.answer("Сейчас нет пары для подтверждения.")
        return

    ok, text, partner = await message.bot.meeting_service.confirm_partner(match["id"], me["id"], approved=True)
    await message.answer(text)
    if not ok or not partner:
        return

    users = await message.bot.meeting_service.users_for_match(match["id"])
    if users:
        for user in users:
            other = users[0] if users[1]["id"] == user["id"] else users[1]
            await message.bot.send_message(
                user["tg_id"],
                f"✅ Партнёр подтверждён! Telegram ID партнёра: {other['tg_id']}",
            )


@router.message(F.text == MEETING_REJECT)
async def reject_partner(message: Message) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    match = await message.bot.meeting_service.pending_match_for_user(me["id"])
    if not match:
        await message.answer("Сейчас нет пары для подтверждения.")
        return

    ok, text, _ = await message.bot.meeting_service.confirm_partner(match["id"], me["id"], approved=False)
    await message.answer(text)
    if not ok:
        return

    users = await message.bot.meeting_service.users_for_match(match["id"])
    if users:
        for user in users:
            await message.bot.send_message(user["tg_id"], "❌ Один из вас не подтвердил партнёра. Идём дальше.")


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
    match_fresh = await message.bot.meeting_service.get_match(match["id"])
    if not users or not match_fresh:
        return

    if match_fresh["status"] == "pending_confirm":
        call_link = match_fresh.get("call_room_url")
        for user in users:
            text = "Звонок согласован ✅"
            if call_link:
                text += f"\n🔗 {call_link}"
            text += "\nПодтверди, хочешь продолжить с этим партнёром или нет."
            await message.bot.send_message(user["tg_id"], text, reply_markup=meeting_decision_keyboard())


@router.message(F.text == PRECHECK_YES)
@router.message(F.text == PRECHECK_NO)
@router.message(F.text == ATTENDANCE_YES)
@router.message(F.text == ATTENDANCE_NO)
async def deprecated_flow_hint(message: Message) -> None:
    await message.answer("Этот этап отключён. Используй подтверждение партнёра в текущем сценарии.")
