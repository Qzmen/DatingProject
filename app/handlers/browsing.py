from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards import browse_keyboard, incoming_like_keyboard

router = Router()


@router.message(Command("browse"))
async def browse(message: Message) -> None:
    me = await message.bot.matching_service.get_user_by_tg(message.from_user.id)
    if not me:
        await message.answer("Сначала /start")
        return
    candidate = await message.bot.matching_service.next_candidate(me["id"], me["city"])
    if not candidate:
        await message.answer("Пока нет анкет.")
        return
    await _send_candidate(message, candidate)


@router.callback_query(F.data.startswith("skip:"))
async def skip_candidate(callback: CallbackQuery) -> None:
    await callback.answer("Пропущено")
    fake_message = callback.message
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    candidate = await callback.bot.matching_service.next_candidate(me["id"], me["city"])
    if not candidate:
        await fake_message.answer("Пока нет анкет.")
        return
    await _send_candidate(fake_message, candidate)


@router.callback_query(F.data.startswith("like:"))
async def like_candidate(callback: CallbackQuery) -> None:
    liked_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    is_match, match_id = await callback.bot.matching_service.like(me["id"], liked_id)
    liked_user = await callback.bot.user_service.get_by_id(liked_id)

    await callback.answer("Лайк отправлен")
    if liked_user:
        await _send_incoming_like(callback.bot, me, liked_user)

    if is_match and match_id:
        users = await callback.bot.matching_service.users_for_match(match_id)
        if users:
            for u in users:
                await callback.bot.send_message(
                    u["tg_id"],
                    "🎉 У вас взаимная симпатия!\n🎲 Предложить игру знакомства через /matches",
                )


@router.callback_query(F.data.startswith("like_back:"))
async def like_back(callback: CallbackQuery) -> None:
    liker_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    is_match, match_id = await callback.bot.matching_service.like(me["id"], liker_id)
    await callback.answer("Взаимный лайк!" if is_match else "Лайк отправлен")
    if is_match and match_id:
        users = await callback.bot.matching_service.users_for_match(match_id)
        if users:
            for u in users:
                await callback.bot.send_message(u["tg_id"], "🎉 У вас взаимная симпатия! /matches")


@router.callback_query(F.data.startswith("pass_like:"))
async def pass_like(callback: CallbackQuery) -> None:
    liker_id = int(callback.data.split(":", 1)[1])
    me = await callback.bot.matching_service.get_user_by_tg(callback.from_user.id)
    await callback.bot.matching_service.pass_like(me["id"], liker_id)
    await callback.answer("Пропущено")


async def _send_candidate(message: Message, candidate: dict) -> None:
    caption = (
        f"{candidate['name']} {candidate['age']} ({candidate['city']})\n"
        f"{candidate.get('description') or ''}\n"
        f"⭐ Репутация: {candidate.get('reputation_score', 0)}"
    )
    if candidate.get("photo_file_id"):
        await message.answer_photo(candidate["photo_file_id"], caption=caption, reply_markup=browse_keyboard(candidate["id"]))
    else:
        await message.answer(caption, reply_markup=browse_keyboard(candidate["id"]))
    if candidate.get("voice_file_id"):
        await message.answer("🎤 Голосовое приветствие")
        await message.answer_voice(candidate["voice_file_id"])


async def _send_incoming_like(bot, liker: dict, liked_user: dict) -> None:
    text = f"Тебя лайкнули ❤️\n{liker['name']} {liker['age']} ({liker['city']})\n{liker.get('description') or ''}\n⭐ Репутация: {liker.get('reputation_score', 0)}"
    if liker.get("photo_file_id"):
        await bot.send_photo(liked_user["tg_id"], liker["photo_file_id"], caption=text, reply_markup=incoming_like_keyboard(liker["id"]))
    else:
        await bot.send_message(liked_user["tg_id"], text, reply_markup=incoming_like_keyboard(liker["id"]))
