import json
import random
from contextlib import suppress

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards import (
    BTN_ADDITIONAL,
    BTN_BACK,
    BTN_CHALLENGE,
    BTN_DICE,
    BTN_END_GAME,
    BTN_MATCH_CLOSE,
    BTN_MATCH_CONTINUE,
    BTN_MATCH_PROPOSE,
    BTN_MATCH_REBROWSE,
    BTN_MATCH_REMOVE,
    BTN_MATCH_REVEAL,
    BTN_MATCH_SHOW_CONTACT,
    BTN_MATCHES,
    BTN_MATCH_WAIT,
    BTN_NEXT_ROUND,
    BTN_REFRESH,
    BTN_REVEAL_CONTACT,
    additional_game_keyboard,
    choice_answer_inline_keyboard,
    game_invite_inline_keyboard,
    main_menu_keyboard,
    match_actions_keyboard,
    match_select_inline_keyboard,
    reveal_contact_inline_keyboard,
    round_finished_keyboard,
    waiting_answer_keyboard,
    waiting_partner_keyboard,
)

router = Router()

STATUS_RU = {
    "matched": "Новый матч",
    "game_invited": "Игра предложена",
    "game_active": "Игра активна",
    "contact_revealed": "Контакт раскрыт",
    "closed": "Закрыт",
    "game_declined": "Игра отклонена",
    "game_ended": "Игра завершена",
}

USER_CURRENT_MATCH: dict[int, int] = {}
USER_SCREEN: dict[int, str] = {}


async def _send_state_update_to_user(bot, user: dict, match_id: int | None, text: str) -> None:
    if not match_id:
        await bot.send_message(user["tg_id"], text, reply_markup=main_menu_keyboard())
        return
    match = await bot.matching_service.get_match_for_user(match_id, user["id"])
    if not match:
        await bot.send_message(user["tg_id"], "Состояние уже изменилось. Обновил меню.", reply_markup=main_menu_keyboard())
        return
    USER_CURRENT_MATCH[user["tg_id"]] = match_id
    kb = await _reply_keyboard_for_match_user(bot, match, user["id"])
    await bot.send_message(user["tg_id"], text, reply_markup=kb)


async def _notify_match_users(bot, match_id: int, text: str) -> None:
    users = await bot.matching_service.users_for_match(match_id)
    if not users:
        return
    for u in users:
        await _send_state_update_to_user(bot, u, match_id, text)


async def _show_matches_list(message: Message, user_id: int) -> None:
    rows = await message.bot.matching_service.list_matches_for_user(user_id)
    if not rows:
        await message.answer("Матчей пока нет", reply_markup=main_menu_keyboard())
        USER_SCREEN[message.from_user.id] = "menu"
        return
    prepared = []
    for r in rows:
        row = dict(r)
        row["status_ru"] = STATUS_RU.get(row["status"], row["status"])
        prepared.append(row)
    USER_SCREEN[message.from_user.id] = "matches_list"
    await message.answer("💞 Выбери матч:", reply_markup=match_select_inline_keyboard(prepared))


async def _reply_keyboard_for_match_user(bot, match: dict, user_id: int):
    if match["status"] == "game_active":
        round_number = int(match.get("game_round") or 1)
        answered = await bot.matching_service.round_answered_user_ids(match["id"], round_number)
        users = await bot.matching_service.users_for_match(match["id"])
        if users:
            ids = {users[0]["id"], users[1]["id"]}
            if answered == ids:
                return round_finished_keyboard()
            if user_id in answered:
                return waiting_partner_keyboard()
            return waiting_answer_keyboard()
    return match_actions_keyboard(match["status"])


def _instruction_for_type(answer_type: str) -> str:
    return {
        "text": "Отправь ответ текстом до 300 символов.",
        "voice": "Отправь голосовое до 30 секунд.",
        "video_note": "Отправь кружок Telegram.",
        "photo": "В этом раунде нужно отправить фото. Можно выбрать фото из галереи телефона.",
        "choice": "Выбери вариант кнопкой ниже.",
        "any": "Можно ответить текстом, голосовым, кружком или фото.",
    }.get(answer_type, "Отправь ответ сообщением.")


async def _send_round_prompt_to_user(bot, user: dict, match: dict) -> None:
    base_text = (
        "✅ Игра знакомства началась!\n\n"
        f"Раунд {match['game_round']}\n"
        f"Вопрос:\n{match['game_prompt']}\n\n"
        f"{_instruction_for_type(match.get('expected_answer_type', 'text'))}"
    )
    if match.get("expected_answer_type") == "choice" and match.get("choice_options"):
        options = json.loads(match["choice_options"])
        await bot.send_message(user["tg_id"], base_text, reply_markup=choice_answer_inline_keyboard(match["id"], options))
        await bot.send_message(user["tg_id"], "Для навигации используй меню ниже.", reply_markup=waiting_answer_keyboard())
    else:
        await bot.send_message(user["tg_id"], base_text, reply_markup=waiting_answer_keyboard())


@router.message(Command("matches"))
@router.message(F.text == BTN_MATCHES)
async def matches(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        await message.answer("Сначала /start")
        return
    await _show_matches_list(message, me["id"])


@router.callback_query(F.data.startswith("match:"))
async def open_match(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    if not me:
        await callback.answer("Сначала /start", show_alert=True)
        return
    match = await callback.bot.matching_service.get_match_for_user(match_id, me["id"])
    if not match:
        await callback.answer("Матч не найден", show_alert=True)
        return
    USER_CURRENT_MATCH[callback.from_user.id] = match_id
    USER_SCREEN[callback.from_user.id] = "match"
    kb = await _reply_keyboard_for_match_user(callback.bot, match, me["id"])
    await callback.message.answer(f"Матч #{match_id}\nСтатус: {STATUS_RU.get(match['status'], match['status'])}", reply_markup=kb)
    await callback.answer()


@router.message(F.text == BTN_MATCH_PROPOSE)
async def propose_game_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    if not match_id:
        await message.answer("Сначала выбери матч в списке.")
        return
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    ok = await message.bot.matching_service.propose_game(match_id, me["id"])
    if not ok:
        await message.answer("Состояние уже изменилось. Обновил меню.")
        match = await message.bot.matching_service.get_match_for_user(match_id, me["id"])
        if match:
            await message.answer("Текущий статус матча.", reply_markup=await _reply_keyboard_for_match_user(message.bot, match, me["id"]))
        return
    users = await message.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            if u["id"] != me["id"]:
                await message.bot.send_message(
                    u["tg_id"],
                    f"🎲 {me['name']} предлагает начать игру знакомства.\nЭто короткие раунды. Контакты не раскрываются.",
                    reply_markup=game_invite_inline_keyboard(match_id),
                )
    await _notify_match_users(message.bot, match_id, "Приглашение в игру отправлено.")


@router.callback_query(F.data.startswith("accept_game:"))
async def accept_game(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    payload = await callback.bot.matching_service.accept_game(match_id)
    await callback.answer("Принято" if payload else "Не удалось")
    if not payload:
        return
    users = await callback.bot.matching_service.users_for_match(match_id)
    if not users:
        return
    for u in users:
        match = await callback.bot.matching_service.get_match_for_user(match_id, u["id"])
        await _send_round_prompt_to_user(callback.bot, u, match)


@router.callback_query(F.data.startswith("decline_game:"))
async def decline_game(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    await callback.bot.matching_service.decline_game(match_id)
    await callback.answer("Отказано")
    await _notify_match_users(callback.bot, match_id, "Пользователь пока не готов начать игру.")


@router.message(Command("game"))
@router.message(F.text == BTN_MATCH_CONTINUE)
async def continue_game_text(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        return
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    match = await message.bot.matching_service.get_match_for_user(match_id, me["id"]) if match_id else await message.bot.matching_service.get_active_game_for_user(me["id"])
    if not match or match["status"] != "game_active":
        await message.answer("Нет активной игры.", reply_markup=main_menu_keyboard())
        return
    USER_CURRENT_MATCH[message.from_user.id] = int(match["id"])
    USER_SCREEN[message.from_user.id] = "game"
    kb = await _reply_keyboard_for_match_user(message.bot, match, me["id"])
    round_number = int(match.get("game_round") or 1)
    answered = await message.bot.matching_service.round_answered_user_ids(match["id"], round_number)
    users = await message.bot.matching_service.users_for_match(match["id"])
    ids = {users[0]["id"], users[1]["id"]} if users else set()
    if answered == ids and ids:
        await message.answer("✅ Вы оба ответили. Можно выбрать дальнейшее действие.", reply_markup=kb)
    elif me["id"] in answered:
        await message.answer("✅ Ты уже ответил(а). Ждём ответ второго участника.", reply_markup=kb)
    elif answered:
        await message.answer("👀 Твой матч уже ответил. Ждём твой ответ.", reply_markup=kb)
    else:
        await message.answer("Раунд начался. Отправь свой ответ.", reply_markup=kb)
    await message.answer(f"Раунд {match['game_round']}\nВопрос:\n{match['game_prompt']}\n\n{_instruction_for_type(match.get('expected_answer_type', 'text'))}")


@router.message(F.text.in_({BTN_MATCH_REVEAL, BTN_REVEAL_CONTACT}))
async def request_reveal_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    if not match_id:
        await message.answer("Сначала выбери матч.")
        return
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    ok = await message.bot.matching_service.request_contact_reveal(match_id, me["id"])
    if not ok:
        await message.answer("Состояние уже изменилось. Обновил меню.")
        return
    users = await message.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            if u["id"] != me["id"]:
                await message.bot.send_message(
                    u["tg_id"],
                    "Твой матч хочет раскрыть контакт.\nСогласиться?",
                    reply_markup=reveal_contact_inline_keyboard(match_id),
                )
    await message.answer("Запрос на раскрытие отправлен.")


@router.callback_query(F.data.startswith("accept_reveal:"))
async def accept_reveal(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    await callback.bot.matching_service.accept_contact_reveal(match_id, me["id"])
    users = await callback.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            other = users[0] if users[1]["id"] == u["id"] else users[1]
            username = other.get("username")
            if username:
                await callback.bot.send_message(u["tg_id"], f"Контакт раскрыт: @{username}")
    await callback.answer("Контакт раскрыт")
    await _notify_match_users(callback.bot, match_id, "Контакт раскрыт по взаимному согласию.")


@router.callback_query(F.data.startswith("decline_reveal:"))
async def decline_reveal(callback: CallbackQuery) -> None:
    await callback.answer("Контакт не раскрыт.")


@router.message(Command("stop_game"))
@router.message(F.text == BTN_END_GAME)
async def stop_game_text(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        return
    rows = await message.bot.matching_service.list_matches_for_user(me["id"])
    active = next((r for r in rows if r["status"] == "game_active"), None)
    if not active:
        await message.answer("Активной игры нет.")
        return
    ended = await message.bot.matching_service.end_game(active["id"])
    if not ended:
        await message.answer("Сейчас нет активной игры для завершения.")
        return
    await _notify_match_users(message.bot, active["id"], "Игра завершена. Матч остаётся в списке.")


@router.message(F.text == BTN_MATCH_CLOSE)
async def close_match_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    if not match_id:
        await message.answer("Сначала выбери матч.")
        return
    await message.bot.matching_service.close_match(match_id)
    await _notify_match_users(message.bot, match_id, "Матч был закрыт.")
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    await _show_matches_list(message, me["id"])


@router.message(F.text == BTN_NEXT_ROUND)
async def next_round_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not match_id or not me:
        await message.answer("Сначала выбери матч.")
        return
    nxt = await message.bot.matching_service.start_next_round(match_id, me["id"])
    if not nxt:
        await message.answer("Состояние уже изменилось. Обновил меню.")
        return
    users = await message.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            match = await message.bot.matching_service.get_match_for_user(match_id, u["id"])
            await _send_round_prompt_to_user(message.bot, u, match)


@router.message(F.text == BTN_REFRESH)
async def refresh_status(message: Message) -> None:
    await continue_game_text(message)


@router.message(F.text == BTN_ADDITIONAL)
async def additional_menu(message: Message) -> None:
    USER_SCREEN[message.from_user.id] = "additional"
    await message.answer("Дополнительные активности:", reply_markup=additional_game_keyboard())


@router.message(F.text == BTN_CHALLENGE)
async def daily_challenge_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    if not match_id:
        await message.answer("Сначала выбери матч.")
        return
    data = await message.bot.matching_service.create_or_refresh_challenge(match_id)
    if not data:
        await message.answer("Челлендж доступен только после завершения раунда.")
        return
    await _notify_match_users(message.bot, match_id, f"🫶 Парный челлендж дня:\n{data['text']}\nСрок: 24 часа.")


@router.message(F.text == BTN_DICE)
async def dice_game_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not match_id or not me:
        await message.answer("Сначала выбери матч.")
        return
    users = await message.bot.matching_service.users_for_match(match_id)
    if not users:
        return
    other = users[0] if users[1]["id"] == me["id"] else users[1]
    my_roll = random.randint(1, 6)
    other_roll = random.randint(1, 6)
    if my_roll == other_roll:
        await message.answer("Ничья! Попробуйте ещё раз.")
        return
    loser = me if my_roll < other_roll else other
    loser_photo = await message.bot.user_service.random_gallery_photo(loser["id"])
    await _notify_match_users(message.bot, match_id, f"🎲 Кубики: {me['name']} — {my_roll}, {other['name']} — {other_roll}.")
    if loser_photo:
        for u in users:
            await message.bot.send_photo(u["tg_id"], loser_photo, caption="📸 Фото из галереи")


@router.message(F.text == BTN_MATCH_SHOW_CONTACT)
async def show_contact(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not match_id or not me:
        return
    rows = await message.bot.matching_service.list_matches_for_user(me["id"])
    match = next((r for r in rows if r["id"] == match_id), None)
    if not match or match["status"] != "contact_revealed":
        await message.answer("Состояние уже изменилось. Обновил меню.")
        return
    username = match.get("partner_username")
    await message.answer(f"Контакт: @{username}" if username else "У пользователя нет @username")


@router.message(F.text == BTN_MATCH_REBROWSE)
async def rebrowse(message: Message) -> None:
    await message.answer("Переходим к подбору анкет.")
    from app.handlers.browsing import browse

    await browse(message)


@router.message(F.text == BTN_MATCH_REMOVE)
async def remove_closed(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    await _show_matches_list(message, me["id"])


@router.message(F.text == BTN_MATCH_WAIT)
async def wait_info(message: Message) -> None:
    await message.answer("Ждём ответа второго участника.")


@router.message(F.text == BTN_BACK)
async def back_navigation(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        await message.answer("Главное меню", reply_markup=main_menu_keyboard())
        return
    screen = USER_SCREEN.get(message.from_user.id, "menu")
    if screen in {"game", "match", "additional"}:
        await _show_matches_list(message, me["id"])
        return
    if screen in {"matches_list", "profile", "settings"}:
        USER_SCREEN[message.from_user.id] = "menu"
        await message.answer("Главное меню", reply_markup=main_menu_keyboard())
        return
    await message.answer("Главное меню", reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("choice_answer:"))
async def choice_answer(callback: CallbackQuery) -> None:
    _, match_id_str, idx_str = callback.data.split(":", 2)
    match_id = int(match_id_str)
    idx = int(idx_str)
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    match = await callback.bot.matching_service.get_match_for_user(match_id, me["id"])
    if not match or match.get("expected_answer_type") != "choice":
        await callback.answer("Состояние уже изменилось", show_alert=True)
        return
    options = json.loads(match.get("choice_options") or "[]")
    if idx >= len(options):
        await callback.answer("Некорректный выбор", show_alert=True)
        return
    result = await callback.bot.matching_service.save_round_answer(match_id, int(match["game_round"]), me["id"], "choice", options[idx], None, match["game_prompt"])
    await callback.answer("Выбор сохранён" if result == "saved" else "Ты уже ответил(а)")
    users = await callback.bot.matching_service.users_for_match(match_id)
    if not users:
        return
    answered = await callback.bot.matching_service.round_answered_user_ids(match_id, int(match["game_round"]))
    if len(answered) < 2:
        await callback.message.answer("✅ Ответ сохранён. Ждём ответ второго участника.", reply_markup=waiting_partner_keyboard())
        return
    answers = await callback.bot.matching_service.get_round_answers(match_id, int(match["game_round"]))
    for receiver in users:
        for ans in answers:
            if ans["sender_user_id"] == receiver["id"]:
                continue
            label = "☑️ Выбор твоего матча" if ans["message_type"] == "choice" else "💬 Ответ от твоего матча"
            await callback.bot.send_message(receiver["tg_id"], f"{label}:\n{ans['text']}")
        await callback.bot.send_message(receiver["tg_id"], "✅ Вы оба ответили. Раунд завершён.", reply_markup=round_finished_keyboard())


@router.message(F.voice | F.video_note | F.text | F.photo | F.video)
async def capture_round_answer(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        return
    active = await message.bot.matching_service.get_active_game_for_user(me["id"])
    if not active:
        return
    if message.text and message.text in {
        BTN_BACK,
        BTN_NEXT_ROUND,
        BTN_ADDITIONAL,
        BTN_DICE,
        BTN_CHALLENGE,
        BTN_REFRESH,
        BTN_END_GAME,
        BTN_REVEAL_CONTACT,
        BTN_MATCH_CONTINUE,
        BTN_MATCH_PROPOSE,
        BTN_MATCH_CLOSE,
        BTN_MATCH_SHOW_CONTACT,
    }:
        return

    expected = active.get("expected_answer_type") or "text"
    msg_type = ""
    text = None
    file_id = None

    if message.video and expected == "video_note":
        await message.answer("Нужен именно кружок Telegram, не обычное видео.")
        return

    if message.photo:
        msg_type = "photo"
        file_id = message.photo[-1].file_id
        await message.bot.user_service.add_gallery_photo(me["id"], file_id)
    elif message.voice:
        msg_type = "voice"
        file_id = message.voice.file_id
        if message.voice.duration and message.voice.duration > 30:
            await message.answer("Голосовое должно быть до 30 секунд.")
            return
    elif message.video_note:
        msg_type = "video_note"
        file_id = message.video_note.file_id
    elif message.text and not message.text.startswith("/"):
        msg_type = "text"
        text = message.text.strip()
        if len(text) > 300:
            await message.answer("Текст должен быть до 300 символов.")
            return
    else:
        return

    if expected != "any" and expected != msg_type and expected != "choice":
        await message.answer(_instruction_for_type(expected))
        return

    result = await message.bot.matching_service.save_round_answer(
        int(active["id"]),
        int(active.get("game_round") or 1),
        me["id"],
        msg_type,
        text,
        file_id,
        active.get("game_prompt") or "",
    )

    users = await message.bot.matching_service.users_for_match(int(active["id"]))
    if not users:
        return
    other = users[0] if users[1]["id"] == me["id"] else users[1]
    round_number = int(active.get("game_round") or 1)
    answered = await message.bot.matching_service.round_answered_user_ids(int(active["id"]), round_number)

    if result == "duplicate":
        if len(answered) == 2:
            await message.answer("Ты уже ответил(а) в этом раунде.", reply_markup=round_finished_keyboard())
        else:
            await message.answer("Ты уже ответил(а) в этом раунде. Ждём второго участника.", reply_markup=waiting_partner_keyboard())
        return
    if result == "stale":
        await message.answer("Состояние уже изменилось. Обновил меню.", reply_markup=main_menu_keyboard())
        return

    if len(answered) < 2:
        await message.answer("✅ Ответ сохранён. Ждём ответ второго участника.", reply_markup=waiting_partner_keyboard())
        with suppress(Exception):
            await message.bot.send_message(other["tg_id"], "👀 Твой матч уже ответил. Осталось ответить тебе.", reply_markup=waiting_answer_keyboard())
        return

    answers = await message.bot.matching_service.get_round_answers(int(active["id"]), round_number)
    for receiver in users:
        for ans in answers:
            if ans["sender_user_id"] == receiver["id"]:
                continue
            if ans["message_type"] == "voice":
                await message.bot.send_message(receiver["tg_id"], "🎤 Голосовое от твоего матча")
                await message.bot.send_voice(receiver["tg_id"], ans["file_id"])
            elif ans["message_type"] == "video_note":
                await message.bot.send_message(receiver["tg_id"], "🎥 Кружок от твоего матча")
                await message.bot.send_video_note(receiver["tg_id"], ans["file_id"])
            elif ans["message_type"] == "photo":
                await message.bot.send_photo(receiver["tg_id"], ans["file_id"], caption="📸 Фото от твоего матча")
            elif ans["message_type"] == "choice":
                await message.bot.send_message(receiver["tg_id"], f"☑️ Выбор твоего матча:\n{ans['text']}")
            else:
                await message.bot.send_message(receiver["tg_id"], f"💬 Ответ от твоего матча:\n{ans['text']}")
        await message.bot.send_message(receiver["tg_id"], "✅ Вы оба ответили. Раунд завершён.", reply_markup=round_finished_keyboard())
