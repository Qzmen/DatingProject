import asyncio

from app.bot import run_bot
from app.config import get_settings
from app.db import init_db
from app.logging_config import setup_logging


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    await init_db(settings.database_url)
    await run_bot(settings)


if __name__ == "__main__":
    asyncio.run(main())
