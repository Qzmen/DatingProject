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
        await message.answer(
            "Анкета сейчас отключена. Включи её в меню и попробуй снова.",
            reply_markup=main_menu_keyboard(profile_enabled=False),
        )
        return

    if await matching_service.has_active_meeting(me["id"]):
        await message.answer(
            "У тебя уже есть активная встреча. Подтверди или отмени её.",
            reply_markup=meeting_decision_keyboard(),
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
        await _show_next_candidate(message, state, me["id"], me["city"])
        return

    if match.get("reason") == "active_meeting":
        await message.answer(
            "Один из вас уже занят активной встречей. Попробуй позже.",
            reply_markup=main_menu_keyboard(profile_enabled=True),
        )
        await state.clear()
        return

    await message.answer(
        "🔥 Взаимный лайк!\n"
        "Нужно подтвердить офлайн-встречу в течение 24 часов.",
        reply_markup=meeting_decision_keyboard(),
    )
    await state.clear()


@router.message(BrowsingStates.waiting_reaction, F.text == BROWSE_SKIP)
async def skip_candidate(message: Message, state: FSMContext) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    await _show_next_candidate(message, state, me["id"], me["city"])


@router.message(BrowsingStates.waiting_reaction, F.text == BROWSE_BACK_MENU)
async def back_to_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    enabled = bool(me and me["is_blocked"] == 0)
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

    caption = f"✨ {candidate['name']}, {candidate['age']}\n{candidate['gender']} • {candidate['city']}"
    if candidate.get("photo_file_id"):
        await message.answer_photo(candidate["photo_file_id"], caption=caption, reply_markup=browse_keyboard())
    else:
        await message.answer(caption, reply_markup=browse_keyboard())
