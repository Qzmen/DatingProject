from aiogram import Bot, Dispatcher

from app.config import Settings
from app.handlers import admin, browsing, matches, registration
from app.services.matching import MatchingService
from app.services.users import UserService


async def run_bot(settings: Settings) -> None:
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    user_service = UserService(settings.database_url, settings.default_stars_balance)
    matching_service = MatchingService(settings.database_url)

    bot.settings = settings
    bot.user_service = user_service
    bot.matching_service = matching_service

    dp.include_router(registration.router)
    dp.include_router(browsing.router)
    dp.include_router(matches.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)
