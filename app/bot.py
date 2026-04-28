import asyncio

from aiogram import Bot, Dispatcher

from app.config import Settings
from app.handlers import admin, browsing, meetings, registration
from app.scheduler import scheduler_loop
from app.services.matching import MatchingService
from app.services.meetings import MeetingService
from app.services.users import UserService


async def run_bot(settings: Settings) -> None:
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    user_service = UserService(settings.database_url, settings.default_stars_balance)
    matching_service = MatchingService(settings.database_url)
    meeting_service = MeetingService(
        settings.database_url,
        settings.meeting_price_stars,
        yandex_telemost_oauth_token=settings.yandex_telemost_oauth_token,
        yandex_telemost_enabled=settings.yandex_telemost_enabled,
        use_jitsi=settings.use_jitsi,
    )

    bot.settings = settings
    bot.user_service = user_service
    bot.matching_service = matching_service
    bot.meeting_service = meeting_service

    dp.include_router(registration.router)
    dp.include_router(browsing.router)
    dp.include_router(meetings.router)
    dp.include_router(admin.router)

    scheduler_task = asyncio.create_task(scheduler_loop(bot, meeting_service))
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
