from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


def _is_admin(message: Message) -> bool:
    settings = message.bot.settings
    return message.from_user.id in settings.admin_id_set


@router.message(Command("admin_users"))
async def admin_users(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("Недостаточно прав")
        return
    user_service = message.bot.user_service
    users = await user_service.list_users()
    if not users:
        await message.answer("Пользователей нет")
        return
    lines = [
        f"{u['tg_id']} | {u['name']} | {u['age']} | {u['city']} | rating {u['rating_score']}/{u['rating_count']} | blocked={u['is_blocked']}"
        for u in users
    ]
    await message.answer("\n".join(lines[:30]))


@router.message(Command("admin_matches"))
async def admin_matches(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("Недостаточно прав")
        return
    matching_service = message.bot.matching_service
    matches = await matching_service.list_matches()
    if not matches:
        await message.answer("Матчей нет")
        return
    lines = [
        f"#{m['id']} [{m['status']}] users({m['user1_id']},{m['user2_id']}) {m['meetup_time'][:16]} {m['meetup_place']}"
        for m in matches
    ]
    await message.answer("\n".join(lines[:30]))


@router.message(Command("block"))
async def admin_block(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("Недостаточно прав")
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /block <tg_id>")
        return
    tg_id = int(parts[1])
    user_service = message.bot.user_service
    ok = await user_service.block_user(tg_id)
    await message.answer("Пользователь заблокирован" if ok else "Пользователь не найден")
