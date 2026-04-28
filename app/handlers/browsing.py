import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards import browse_keyboard, meeting_decision_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("browse"))
async def browse(message: Message) -> None:
    user_service = message.bot["user_service"]
    matching_service = message.bot["matching_service"]

    me = await user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала пройди регистрацию через /start")
        return
    if me["is_blocked"]:
        await message.answer("Твой аккаунт заблокирован из-за низкого рейтинга.")
        return
    if await matching_service.has_active_meeting(me["id"]):
        await message.answer("У тебя уже есть активная встреча. Сначала заверши её.")
        return

    candidate = await matching_service.next_candidate(me["id"], me["city"])
    if not candidate:
        await message.answer("Пока нет подходящих анкет в твоём городе.")
        return

    text = f"{candidate['name']}, {candidate['age']}, {candidate['gender']}\nГород: {candidate['city']}"
    if candidate["photo_file_id"]:
        await message.answer_photo(candidate["photo_file_id"], caption=text, reply_markup=browse_keyboard(candidate["id"]))
    else:
        await message.answer(text, reply_markup=browse_keyboard(candidate["id"]))


@router.callback_query(F.data.startswith("skip:"))
async def skip_candidate(callback: CallbackQuery) -> None:
    await callback.answer("Пропущено")
    await callback.message.answer("Используй /browse, чтобы посмотреть следующую анкету.")


@router.callback_query(F.data.startswith("like:"))
async def like_candidate(callback: CallbackQuery) -> None:
    matching_service = callback.bot["matching_service"]
    user_service = callback.bot["user_service"]
    meetings = callback.bot["meeting_service"]

    me = await user_service.get_by_tg_id(callback.from_user.id)
    candidate_id = int(callback.data.split(":")[1])
    match = await matching_service.save_like_and_try_match(me["id"], candidate_id)

    if not match:
        await callback.answer("Лайк отправлен")
        return

    if match.get("reason") == "active_meeting":
        await callback.answer("Матч не создан: у кого-то уже активная встреча.", show_alert=True)
        return

    users = await meetings.users_for_match(match["id"])
    if not users:
        await callback.answer("Ошибка матча", show_alert=True)
        return

    for user in users:
        await callback.bot.send_message(
            user["tg_id"],
            (
                "🎉 Взаимный лайк!\n"
                f"Предложение: кофе в центре в {match['meetup_time'][:16].replace('T', ' ')}\n"
                f"Подтвердить нужно до {match['confirm_deadline'][:16].replace('T', ' ')}\n"
                "Подтверждение стоит Telegram Stars (mock), вернём при успешной встрече."
            ),
            reply_markup=meeting_decision_keyboard(match["id"]),
        )
    logger.info("New match id=%s users=%s,%s", match["id"], match["user1_id"], match["user2_id"])
    await callback.answer("Матч создан!")
