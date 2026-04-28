from aiogram import F, Router
from aiogram.types import Message

from app.services.users import UserService
from app.services.matching import MatchingService
from app.keyboards import browse_keyboard, meeting_decision_keyboard

router = Router()

# Инициализация сервисов
user_service = UserService("dating.db", default_stars_balance=100)
matching_service = MatchingService("dating.db")


@router.message(F.text == "/browse")
async def browse(message: Message) -> None:
    me = await user_service.get_by_tg_id(message.from_user.id)

    # Получаем активную встречу, если есть
    active_meeting = await matching_service.get_active_meeting_obj(me["id"])
    if active_meeting:
        match_id = active_meeting["id"]
        await message.answer(
            "У тебя уже есть активная встреча. Сначала заверши её.",
            reply_markup=meeting_decision_keyboard(match_id)
        )
        return

    # Ищем следующего кандидата
    candidate = await matching_service.next_candidate(me["id"], me["city"])
    if not candidate:
        await message.answer("Пока нет подходящих анкет в твоём городе.")
        return

    await message.answer(
        f"{candidate['name']}, {candidate['age']}, {candidate['gender']}\nГород: {candidate['city']}",
        reply_markup=browse_keyboard(candidate["id"])
    )