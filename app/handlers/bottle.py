from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.keyboards import (
    BTN_BOTTLE,
    BTN_BOTTLE_CREATE,
    BTN_BOTTLE_JOIN_CODE,
    BTN_BOTTLE_LEAVE,
    BTN_BOTTLE_LIST,
    BTN_BOTTLE_SPIN,
    BTN_BOTTLE_START,
    bottle_lobby_keyboard,
    bottle_menu_keyboard,
    main_menu_keyboard,
    unregistered_keyboard,
)
from app.states import BottleStates

router = Router()


def _lobbies_keyboard(lobbies: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{l['title']} ({l['players']}/{l['max_players']})", callback_data=f"lobby_join:{l['id']}")] for l in lobbies[:15]]
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="Нет лобби", callback_data="noop")]])


def _spin_action_keyboard(spin_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="❤️ Симпатия", callback_data=f"spin_like:{spin_id}"),
            InlineKeyboardButton(text="🎲 Задание знакомства", callback_data=f"spin_task:{spin_id}"),
            InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"spin_skip:{spin_id}"),
        ]]
    )


@router.message(Command("bottle"))
@router.message(F.text == BTN_BOTTLE)
async def bottle_menu(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        await message.answer("Сначала заполни анкету.", reply_markup=unregistered_keyboard())
        return
    await message.answer("Выбери лобби своего города или создай своё.", reply_markup=bottle_menu_keyboard())


@router.message(F.text == BTN_BOTTLE_LIST)
async def list_lobbies(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        await message.answer("Сначала заполни анкету.", reply_markup=unregistered_keyboard())
        return
    lobbies = await message.bot.lobby_service.list_lobbies(me["city_normalized"])
    await message.answer("Лобби твоего города:", reply_markup=_lobbies_keyboard(lobbies))


@router.message(F.text == BTN_BOTTLE_CREATE)
async def create_lobby_start(message: Message, state: FSMContext) -> None:
    await state.set_state(BottleStates.waiting_lobby_title)
    await message.answer("Введи название лобби.")


@router.message(BottleStates.waiting_lobby_title)
async def create_lobby_finish(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if len(title) < 3 or len(title) > 40:
        await message.answer("Название лобби должно быть от 3 до 40 символов.")
        return
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    created = await message.bot.lobby_service.create_lobby(me["id"], me["city"], me["city_normalized"], title, 6, "public")
    await state.clear()
    await message.answer(f"Лобби создано: {title}", reply_markup=bottle_lobby_keyboard(is_host=True))
    await _show_lobby_state(message, created["id"], me["id"])


@router.message(F.text == BTN_BOTTLE_JOIN_CODE)
async def join_by_code_start(message: Message, state: FSMContext) -> None:
    await state.set_state(BottleStates.waiting_join_code)
    await message.answer("Введи код приватного лобби.")


@router.message(BottleStates.waiting_join_code)
async def join_by_code_finish(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip().upper()
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    ok = await message.bot.lobby_service.join_lobby_by_code(me["id"], code)
    await state.clear()
    if not ok:
        await message.answer("Не удалось войти в лобби по коду.")
        return
    active = await message.bot.lobby_service.active_lobby_for_user(me["id"])
    await message.answer("Ты в лобби.", reply_markup=bottle_lobby_keyboard(active.get("role") == "host"))
    await _show_lobby_state(message, active["id"], me["id"])


@router.callback_query(F.data.startswith("lobby_join:"))
async def join_lobby(callback: CallbackQuery) -> None:
    lobby_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    ok = await callback.bot.lobby_service.join_lobby(me["id"], lobby_id)
    await callback.answer("Вошёл в лобби" if ok else "Не удалось войти")
    if not ok:
        return
    active = await callback.bot.lobby_service.active_lobby_for_user(me["id"])
    await callback.message.answer("Ты в лобби.", reply_markup=bottle_lobby_keyboard(active.get("role") == "host"))
    await _show_lobby_state(callback.message, lobby_id, me["id"])


@router.message(F.text == BTN_BOTTLE_START)
async def start_lobby(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    active = await message.bot.lobby_service.active_lobby_for_user(me["id"])
    if not active or active.get("role") != "host":
        await message.answer("Только хост может стартовать лобби.")
        return
    ok = await message.bot.lobby_service.start_lobby(me["id"], active["id"])
    await message.answer("Лобби запущено." if ok else "Не удалось запустить лобби.")
    await _show_lobby_state(message, active["id"], me["id"])


@router.message(F.text == BTN_BOTTLE_SPIN)
async def spin_bottle(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    active = await message.bot.lobby_service.active_lobby_for_user(me["id"])
    if not active or active.get("role") != "host":
        await message.answer("Сейчас крутить бутылочку может только хост.")
        return
    result = await message.bot.bottle_service.spin(active["id"], me["id"])
    if not result:
        await message.answer("Недостаточно участников для спина.")
        return
    selected = await message.bot.user_service.get_by_id(result["selected_user_id"])
    await message.answer("Бутылочка крутится…")
    await message.answer(
        f"Бутылочка выбрала участника:\n{selected['name']} {selected['age']} ({selected['city']})\n{selected.get('description') or ''}\n⭐ Репутация: {selected.get('reputation_score', 0)}",
        reply_markup=_spin_action_keyboard(result["spin_id"]),
    )


@router.callback_query(F.data.startswith("spin_like:"))
async def spin_like(callback: CallbackQuery) -> None:
    spin_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    is_match, match_id, to_user_id = await callback.bot.bottle_service.like_from_spin(spin_id, me["id"])
    await callback.answer("Симпатия отправлена")
    target = await callback.bot.user_service.get_by_id(to_user_id) if to_user_id else None
    if target:
        await callback.bot.send_message(target["tg_id"], "❤️ Тебя выбрали в бутылочке!")
    if is_match and match_id:
        users = await callback.bot.matching_service.users_for_match(match_id)
        if users:
            for u in users:
                await callback.bot.send_message(u["tg_id"], "🎉 У вас взаимная симпатия!", reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("spin_task:"))
async def spin_task(callback: CallbackQuery) -> None:
    await callback.answer("Открываю задание")
    await callback.message.answer("Можно начать игру знакомства без раскрытия контактов. Перейди в 💞 Мои матчи.")


@router.callback_query(F.data.startswith("spin_skip:"))
async def spin_skip(callback: CallbackQuery) -> None:
    await callback.answer("Пропущено")
    await callback.message.answer("Можно крутануть бутылочку снова.")


@router.message(F.text == BTN_BOTTLE_LEAVE)
async def leave_lobby(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    active = await message.bot.lobby_service.active_lobby_for_user(me["id"])
    if not active:
        await message.answer("Ты не в лобби.")
        return
    await message.bot.lobby_service.leave_lobby(me["id"], active["id"])
    await message.answer("Ты вышел из лобби.", reply_markup=bottle_menu_keyboard())


async def _show_lobby_state(message: Message, lobby_id: int, user_id: int) -> None:
    state = await message.bot.lobby_service.get_lobby_state(lobby_id)
    if not state:
        await message.answer("Лобби не найдено.")
        return
    members_text = "\n".join([f"• {m['name']} {m['age']} ({m['city']})" for m in state["members"]]) or "Пока пусто"
    role = next((m["role"] for m in state["members"] if m["id"] == user_id), "member")
    await message.answer(
        f"Лобби: {state['lobby']['title']}\nСтатус: {state['lobby']['status']}\n\nУчастники:\n{members_text}",
        reply_markup=bottle_lobby_keyboard(role == "host"),
    )
