from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards import (
    BTN_GAME,
    BTN_MATCHES,
    BTN_STOP_GAME,
    contact_reveal_keyboard,
    game_invite_keyboard,
    game_round_keyboard,
    main_menu_keyboard,
    match_keyboard,
    match_list_keyboard,
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


async def _finish_round_if_ready(bot, match_id: int, round_number: int) -> None:
    answered = await bot.matching_service.round_answered_user_ids(match_id, round_number)
    users = await bot.matching_service.users_for_match(match_id)
    if not users:
        return
    user_ids = {users[0]["id"], users[1]["id"]}
    if answered != user_ids:
        return

    answers = await bot.matching_service.get_round_answers(match_id, round_number)
    for receiver in users:
        for ans in answers:
            if ans["sender_user_id"] == receiver["id"]:
                continue
            if ans["message_type"] == "voice":
                await bot.send_message(receiver["tg_id"], "🎤 Голосовое от твоего матча")
                await bot.send_voice(receiver["tg_id"], ans["file_id"])
            elif ans["message_type"] == "video_note":
                await bot.send_message(receiver["tg_id"], "🎥 Кружок от твоего матча")
                await bot.send_video_note(receiver["tg_id"], ans["file_id"])
            else:
                await bot.send_message(receiver["tg_id"], f"💬 Ответ от твоего матча:\n{ans['text']}")
        await bot.send_message(receiver["tg_id"], "Раунд завершён.", reply_markup=game_round_keyboard(match_id))

    if round_number < 4:
        nxt = await bot.matching_service.start_next_round(match_id)
        if nxt:
            for u in users:
                await bot.send_message(
                    u["tg_id"],
                    f"🔥 Следующий раунд {nxt['round']}: {nxt['prompt']}",
                    reply_markup=game_round_keyboard(match_id),
                )


@router.message(Command("matches"))
@router.message(F.text == BTN_MATCHES)
async def matches(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        await message.answer("Сначала /start")
        return
    rows = await message.bot.matching_service.list_matches_for_user(me["id"])
    if not rows:
        await message.answer("Матчей пока нет")
        return
    prepared = []
    for r in rows:
        r = dict(r)
        r["status_ru"] = STATUS_RU.get(r["status"], r["status"])
        prepared.append(r)
    await message.answer("📋 Мои матчи", reply_markup=match_list_keyboard(prepared))


@router.callback_query(F.data.startswith("match:"))
async def open_match(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    match = await callback.bot.matching_service.get_match_for_user(match_id, me["id"])
    if not match:
        await callback.answer("Матч не найден", show_alert=True)
        return
    await callback.message.answer(
        f"Матч #{match_id}\nСтатус: {STATUS_RU.get(match['status'], match['status'])}",
        reply_markup=match_keyboard(match_id, match["status"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("propose_game:"))
async def propose_game(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    ok = await callback.bot.matching_service.propose_game(match_id, me["id"])
    await callback.answer("Предложение отправлено" if ok else "Не удалось")
    users = await callback.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            if u["id"] != me["id"]:
                await callback.bot.send_message(
                    u["tg_id"],
                    f"🎲 {me['name']} предлагает начать игру знакомства.\n"
                    "Это короткие раунды с голосовыми, кружками и ответами на вопросы. Контакты не раскрываются.",
                    reply_markup=game_invite_keyboard(match_id),
                )


@router.callback_query(F.data.startswith("accept_game:"))
async def accept_game(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    ok = await callback.bot.matching_service.accept_game(match_id)
    await callback.answer("Принято" if ok else "Не удалось")
    users = await callback.bot.matching_service.users_for_match(match_id)
    match = await callback.bot.matching_service.get_match_for_user(match_id, (await callback.bot.matching_service.get_user_by_tg(callback.from_user.id))["id"])
    if users and match:
        for u in users:
            await callback.bot.send_message(
                u["tg_id"],
                f"✅ Игра знакомства началась!\nРаунд 1: {match['game_prompt']}",
                reply_markup=game_round_keyboard(match_id),
            )


@router.callback_query(F.data.startswith("decline_game:"))
async def decline_game(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    await callback.bot.matching_service.decline_game(match_id)
    await callback.answer("Отказано")


@router.callback_query(F.data.startswith("next_round:"))
async def next_round(callback: CallbackQuery) -> None:
    await callback.answer("Следующий раунд пока запускается автоматически после ответов")


@router.callback_query(F.data.startswith("continue_game:"))
async def continue_game(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    match = await callback.bot.matching_service.get_match_for_user(match_id, me["id"])
    if not match:
        await callback.answer("Матч не найден")
        return
    await callback.message.answer(
        f"Раунд {match['game_round']}: {match['game_prompt']}",
        reply_markup=game_round_keyboard(match_id),
    )


@router.message(Command("game"))
@router.message(F.text == BTN_GAME)
async def game_command(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        await message.answer("Сначала /start")
        return
    rows = await message.bot.matching_service.list_matches_for_user(me["id"])
    active = next((r for r in rows if r["status"] == "game_active"), None)
    if not active:
        await message.answer("Нет активной игры. Открой /matches")
        return
    match = await message.bot.matching_service.get_match_for_user(active["id"], me["id"])
    await message.answer(
        f"Раунд {match['game_round']}: {match['game_prompt']}",
        reply_markup=game_round_keyboard(active["id"]),
    )


@router.message(Command("stop_game"))
@router.message(F.text == BTN_STOP_GAME)
async def stop_game(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        await message.answer("Сначала /start")
        return
    rows = await message.bot.matching_service.list_matches_for_user(me["id"])
    active = next((r for r in rows if r["status"] == "game_active"), None)
    if not active:
        await message.answer("Активной игры нет.")
        return
    await message.bot.matching_service.close_match(active["id"])
    await message.answer("Игра завершена.", reply_markup=main_menu_keyboard())


@router.message(F.voice | F.video_note | F.text)
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
    prompt = match.get("game_prompt") or ""
    round_number = int(match.get("game_round") or 1)

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
    user_ids = {users[0]["id"], users[1]["id"]}
    if answered != user_ids:
        await message.answer("Ответ сохранён. Ждём ответ второго участника.")
        return
    await _finish_round_if_ready(message.bot, active["id"], round_number)


@router.callback_query(F.data.startswith("quick_answer:"))
async def quick_answer(callback: CallbackQuery) -> None:
    _, match_id_raw, tone = callback.data.split(":", 2)
    match_id = int(match_id_raw)
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    if not me:
        await callback.answer("Сначала /start")
        return
    match = await callback.bot.matching_service.get_match_for_user(match_id, me["id"])
    if not match or match["status"] != "game_active":
        await callback.answer("Игра не активна", show_alert=True)
        return

    quick_text_map = {
        "easy": "Легко отвечаю: мне с тобой уже комфортно 😊",
        "tease": "С подколом: проверяю, насколько ты умеешь держать мой юмор 😏",
        "awkward": "Неловко, но честно: ты мне интересен(на), хоть я и смущаюсь 🫣",
    }
    text = quick_text_map.get(tone)
    if not text:
        await callback.answer("Неизвестный формат ответа")
        return
    round_number = int(match.get("game_round") or 1)
    prompt = match.get("game_prompt") or ""
    await callback.bot.matching_service.save_round_answer(match_id, round_number, me["id"], "text", text, None, prompt)
    await _finish_round_if_ready(callback.bot, match_id, round_number)
    await callback.answer("Ответ отправлен ✅")


@router.callback_query(F.data.startswith("reveal_contact:"))
async def request_reveal(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    await callback.bot.matching_service.request_contact_reveal(match_id, me["id"])
    users = await callback.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            if u["id"] != me["id"]:
                await callback.bot.send_message(
                    u["tg_id"],
                    "Твой матч хочет раскрыть контакт.\nСогласиться?",
                    reply_markup=contact_reveal_keyboard(match_id),
                )
    await callback.answer("Запрос отправлен")


@router.callback_query(F.data.startswith("accept_reveal:"))
async def accept_reveal(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    await callback.bot.matching_service.accept_contact_reveal(match_id, me["id"])
    users = await callback.bot.matching_service.users_for_match(match_id)
    if users:
        for u in users:
            other = users[0] if users[1]["id"] == u["id"] else users[1]
            if other.get("username"):
                await callback.bot.send_message(u["tg_id"], f"Контакт раскрыт: @{other['username']}")
            else:
                await callback.bot.send_message(
                    u["tg_id"],
                    "Контакт пока нельзя показать: у пользователя не установлен @username в Telegram.",
                )
    await callback.answer("Контакт раскрыт")


@router.callback_query(F.data.startswith("decline_reveal:"))
async def decline_reveal(callback: CallbackQuery) -> None:
    await callback.answer("Контакт не раскрыт. Можно продолжить игру.")


@router.callback_query(F.data.startswith("close_match:"))
async def close_match(callback: CallbackQuery) -> None:
    match_id = int(callback.data.split(":", 1)[1])
    ok = await callback.bot.matching_service.close_match(match_id)
    await callback.answer("Матч закрыт" if ok else "Не удалось")
