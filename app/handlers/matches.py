import random

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
    BTN_MATCH_REVEAL,
    BTN_MATCHES,
    BTN_NEXT_ROUND,
    BTN_REFRESH,
    BTN_REVEAL_CONTACT,
    additional_game_keyboard,
    game_invite_inline_keyboard,
    game_round_finished_keyboard,
    game_waiting_answer_keyboard,
    game_waiting_partner_keyboard,
    main_menu_keyboard,
    match_select_inline_keyboard,
    matches_menu_keyboard,
    reveal_contact_inline_keyboard,
)

router = Router()

STATUS_RU = {
    "matched": "Новый матч",
    "game_invited": "Игра предложена",
    "game_active": "Игра активна",
    "contact_revealed": "Контакт раскрыт",
    "closed": "Закрыт",
    "game_declined": "Игра отклонена",
}

USER_CURRENT_MATCH: dict[int, int] = {}
USER_SCREEN: dict[int, str] = {}


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


async def _send_round_prompt(message: Message, match: dict, keyboard) -> None:
    await message.answer(
        "✅ Игра знакомства идёт!\n\n"
        f"Раунд {match['game_round']}\n"
        f"Вопрос:\n{match['game_prompt']}\n\n"
        "Отправь ответ сообщением.",
        reply_markup=keyboard,
    )


async def _round_keyboard_for_user(bot, match_id: int, user_id: int):
    match = await bot.matching_service.get_match_for_user(match_id, user_id)
    if not match:
        return game_waiting_answer_keyboard()
    round_number = int(match.get("game_round") or 1)
    answered = await bot.matching_service.round_answered_user_ids(match_id, round_number)
    users = await bot.matching_service.users_for_match(match_id)
    if not users:
        return game_waiting_answer_keyboard()
    ids = {users[0]["id"], users[1]["id"]}
    if answered == ids:
        return game_round_finished_keyboard()
    if user_id in answered:
        return game_waiting_partner_keyboard()
    return game_waiting_answer_keyboard()


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
    await callback.message.answer(
        f"Матч #{match_id}\nСтатус: {STATUS_RU.get(match['status'], match['status'])}",
        reply_markup=matches_menu_keyboard(match["status"]),
    )
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
        await message.answer("Не удалось предложить игру.")
        return
    users = await message.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            if u["id"] != me["id"]:
                await message.bot.send_message(
                    u["tg_id"],
                    f"🎲 {me['name']} предлагает начать игру знакомства.",
                    reply_markup=game_invite_inline_keyboard(match_id),
                )
    await message.answer("Приглашение отправлено.")


@router.callback_query(F.data.startswith("accept_game:"))
async def accept_game(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    ok = await callback.bot.matching_service.accept_game(match_id)
    await callback.answer("Принято" if ok else "Не удалось")
    if not ok:
        return
    users = await callback.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            match = await callback.bot.matching_service.get_match_for_user(match_id, u["id"])
            await callback.bot.send_message(
                u["tg_id"],
                "✅ Игра знакомства началась!\n\n"
                f"Раунд 1\nВопрос:\n{match['game_prompt']}\n\n"
                "Отправь ответ сообщением.",
                reply_markup=game_waiting_answer_keyboard(),
            )


@router.callback_query(F.data.startswith("decline_game:"))
async def decline_game(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    await callback.bot.matching_service.decline_game(match_id)
    await callback.answer("Отказано")


@router.message(Command("game"))
@router.message(F.text == BTN_MATCH_CONTINUE)
async def continue_game_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    if not match_id:
        await message.answer("Сначала выбери матч.")
        return
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    match = await message.bot.matching_service.get_match_for_user(match_id, me["id"])
    if not match or match["status"] != "game_active":
        await message.answer("Нет активной игры по этому матчу.")
        return
    USER_SCREEN[message.from_user.id] = "game"
    keyboard = await _round_keyboard_for_user(message.bot, match_id, me["id"])
    await _send_round_prompt(message, match, keyboard)


@router.message(F.text == BTN_MATCH_REVEAL)
@router.message(F.text == BTN_REVEAL_CONTACT)
async def request_reveal_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    if not match_id:
        await message.answer("Сначала выбери матч.")
        return
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    await message.bot.matching_service.request_contact_reveal(match_id, me["id"])
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
    await message.bot.matching_service.close_match(active["id"])
    await message.answer("Игра завершена.", reply_markup=main_menu_keyboard())
    USER_SCREEN[message.from_user.id] = "menu"


@router.message(F.text == BTN_MATCH_CLOSE)
async def close_match_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    if not match_id:
        await message.answer("Сначала выбери матч.")
        return
    ok = await message.bot.matching_service.close_match(match_id)
    await message.answer("Матч закрыт." if ok else "Не удалось закрыть матч.")
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    await _show_matches_list(message, me["id"])


@router.message(F.text == BTN_NEXT_ROUND)
async def next_round_text(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    if not match_id:
        await message.answer("Сначала выбери матч.")
        return
    nxt = await message.bot.matching_service.start_next_round(match_id)
    if not nxt:
        await message.answer("Не удалось запустить следующий раунд.")
        return
    users = await message.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            await message.bot.send_message(
                u["tg_id"],
                f"🔥 Следующий раунд {nxt['round']}\nВопрос:\n{nxt['prompt']}\n\nОтправь ответ сообщением.",
                reply_markup=game_waiting_answer_keyboard(),
            )


@router.message(F.text == BTN_REFRESH)
async def refresh_status(message: Message) -> None:
    match_id = USER_CURRENT_MATCH.get(message.from_user.id)
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not match_id or not me:
        await message.answer("Сначала выбери матч.")
        return
    match = await message.bot.matching_service.get_match_for_user(match_id, me["id"])
    if not match:
        await message.answer("Матч не найден.")
        return
    round_number = int(match.get("game_round") or 1)
    answered = await message.bot.matching_service.round_answered_user_ids(match_id, round_number)
    users = await message.bot.matching_service.users_for_match(match_id)
    ids = {users[0]["id"], users[1]["id"]} if users else set()
    if answered == ids and ids:
        await message.answer("Раунд завершён. Можно продолжать.", reply_markup=game_round_finished_keyboard())
    elif me["id"] in answered:
        await message.answer("Пока ждём ответ партнёра.", reply_markup=game_waiting_partner_keyboard())
    else:
        await message.answer("Твой ответ ещё не отправлен. Отправь его сообщением.", reply_markup=game_waiting_answer_keyboard())


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
        await message.answer("Челлендж доступен только в активной игре.")
        return
    users = await message.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            await message.bot.send_message(u["tg_id"], f"🫶 Парный челлендж дня:\n{data['text']}\nСрок: 24 часа.")


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
    winner = other if loser["id"] == me["id"] else me
    loser_photo = await message.bot.user_service.random_gallery_photo(loser["id"])
    for u in users:
        await message.bot.send_message(
            u["tg_id"], f"🎲 Кубики: {me['name']} — {my_roll}, {other['name']} — {other_roll}. Проиграл(а): {loser['name']}."
        )
    if loser_photo:
        await message.bot.send_photo(winner["tg_id"], loser_photo, caption=f"📸 Фото из галереи {loser['name']}")


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


@router.message(F.voice | F.video_note | F.text | F.photo)
async def capture_round_answer(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        return
    rows = await message.bot.matching_service.list_matches_for_user(me["id"])
    active = next((r for r in rows if r["status"] == "game_active"), None)
    if not active:
        return
    match = await message.bot.matching_service.get_match_for_user(active["id"], me["id"])
    if not match:
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
    }:
        return
    round_number = int(match.get("game_round") or 1)
    prompt = match.get("game_prompt") or ""
    msg_type = ""
    text = None
    file_id = None
    if message.voice:
        if message.voice.duration and message.voice.duration > 30:
            await message.answer("Голосовое должно быть до 30 секунд.")
            return
        msg_type = "voice"
        file_id = message.voice.file_id
    elif message.video_note:
        msg_type = "video_note"
        file_id = message.video_note.file_id
    elif message.photo:
        await message.bot.user_service.add_gallery_photo(me["id"], message.photo[-1].file_id)
        await message.answer("Фото добавлено в галерею.")
        return
    elif message.text and not message.text.startswith("/"):
        if len(message.text) > 300:
            await message.answer("Текст должен быть до 300 символов.")
            return
        msg_type = "text"
        text = message.text
    else:
        return
    await message.bot.matching_service.save_round_answer(active["id"], round_number, me["id"], msg_type, text, file_id, prompt)
    answered = await message.bot.matching_service.round_answered_user_ids(active["id"], round_number)
    users = await message.bot.matching_service.users_for_match(active["id"])
    if not users:
        return
    ids = {users[0]["id"], users[1]["id"]}
    if answered != ids:
        await message.answer("Ответ сохранён. Ждём ответ партнёра.", reply_markup=game_waiting_partner_keyboard())
        USER_SCREEN[message.from_user.id] = "game"
        return
    answers = await message.bot.matching_service.get_round_answers(active["id"], round_number)
    for receiver in users:
        for ans in answers:
            if ans["sender_user_id"] == receiver["id"]:
                continue
            if ans["message_type"] == "voice":
                await message.bot.send_voice(receiver["tg_id"], ans["file_id"])
            elif ans["message_type"] == "video_note":
                await message.bot.send_video_note(receiver["tg_id"], ans["file_id"])
            else:
                await message.bot.send_message(receiver["tg_id"], f"💬 Ответ партнёра:\n{ans['text']}")
        await message.bot.send_message(receiver["tg_id"], "Раунд завершён.", reply_markup=game_round_finished_keyboard())
