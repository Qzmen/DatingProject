from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import (
    BROWSE_BACK_MENU,
    BROWSE_LIKE,
    BROWSE_SKIP,
    MAIN_MENU_BROWSE,
    browse_keyboard,
    main_menu_keyboard,
    meeting_decision_keyboard,
)
from app.states import BrowsingStates

router = Router()


@router.message(Command("browse"))
@router.message(F.text == MAIN_MENU_BROWSE)
async def browse(message: Message, state: FSMContext) -> None:
    user_service = message.bot.user_service
    matching_service = message.bot.matching_service

    me = await user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала зарегистрируйся через /start")
        return

    if me["is_blocked"]:
        await message.answer("Твоя анкета заблокирована модератором.")
        return

    if me["is_profile_enabled"] == 0:
        await message.answer(
            "Анкета сейчас отключена. Включи её в меню и попробуй снова.",
            reply_markup=main_menu_keyboard(profile_enabled=False),
        )
        return
    await _show_next_candidate(message, state, me["id"], me["city"])


@router.message(BrowsingStates.waiting_reaction, F.text == BROWSE_LIKE)
async def like_candidate(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    candidate_id = data.get("candidate_id")
    if not candidate_id:
        await message.answer("Сначала выбери анкету из меню поиска.")
        await state.clear()
        return

    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    match = await message.bot.matching_service.save_like_and_try_match(me["id"], candidate_id)

    if not match:
        await message.answer("Лайк отправлен ❤️")
        await _notify_like_recipient(message, me, candidate_id)
        await _show_next_candidate(message, state, me["id"], me["city"])
        return

    await message.answer(
        "🔥 Взаимный лайк!\n"
        "Добавили в список взаимных лайков 🤝\nЗвонок можно запустить позже из меню «Взаимные лайки».",
        reply_markup=main_menu_keyboard(profile_enabled=True),
    )
    await _notify_like_recipient(message, me, candidate_id, is_match=True)
    await state.clear()


@router.message(BrowsingStates.waiting_reaction, F.text == BROWSE_SKIP)
async def skip_candidate(message: Message, state: FSMContext) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    await _show_next_candidate(message, state, me["id"], me["city"])


@router.message(BrowsingStates.waiting_reaction, F.text == BROWSE_BACK_MENU)
async def back_to_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    enabled = bool(me and me.get("is_profile_enabled", 1) == 1)
    await message.answer("Возвращаю в меню 🏠", reply_markup=main_menu_keyboard(profile_enabled=enabled))


@router.message(BrowsingStates.waiting_reaction)
async def wrong_browse_choice(message: Message) -> None:
    await message.answer("Используй кнопки: Лайк, Пропустить или В меню.", reply_markup=browse_keyboard())


async def _show_next_candidate(message: Message, state: FSMContext, user_id: int, city: str) -> None:
    candidate = await message.bot.matching_service.next_candidate(user_id, city)
    if not candidate:
        await state.clear()
        await message.answer("Пока нет подходящих анкет в твоём городе.", reply_markup=main_menu_keyboard(profile_enabled=True))
        return

    await state.set_state(BrowsingStates.waiting_reaction)
    await state.update_data(candidate_id=candidate["id"])

    reputation = _format_reputation(candidate["rating_score"], candidate["rating_count"])
    bio = candidate.get("bio") or "Без описания"
    caption = (
        f"{candidate['name']} {candidate['age']} ({candidate['city']})\n"
        f"{bio}\n"
        f"⭐ {candidate['stars_balance']} | Репутация: {reputation}"
    )
    if candidate.get("photo_file_id"):
        await message.answer_photo(candidate["photo_file_id"], caption=caption, reply_markup=browse_keyboard())
    else:
        await message.answer(caption, reply_markup=browse_keyboard())


async def _notify_like_recipient(message: Message, liker: dict, liked_user_id: int, is_match: bool = False) -> None:
    liked_user = await message.bot.user_service.get_by_id(liked_user_id)
    if not liked_user:
        return

    status_line = "💘 У вас взаимный лайк!" if is_match else "Тебя лайкнули ❤️"
    text = (
        f"{status_line}\n"
        f"Это: {liker['name']}, {liker['age']} ({liker['city']})."
    )
    await message.bot.send_message(liked_user["tg_id"], text)


def _format_reputation(score: int, count: int) -> str:
    if count == 0:
        return "⭐ новичок"
    value = (score / count + 5) / 2
    value = max(0.0, min(5.0, value))
    suffix = "оценка" if count == 1 else "оценок"
    return f"⭐ {value:.1f} ({count} {suffix})"
