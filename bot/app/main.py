import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from shared.config import TELEGRAM_BOT_TOKEN
from shared.database import init_db, async_session
from shared.models import Settings
from .handlers import register_handlers
from .middlewares import DbMiddleware
from .services.mailing import process_mailings, check_new_orders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_proxy_url():
    """Получает URL прокси из БД или .env."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Settings).where(Settings.key == "proxy_url")
            )
            setting = result.scalar_one_or_none()
            if setting and setting.value:
                return setting.value
    except Exception:
        pass
    import os
    return os.getenv("PROXY_URL", "")


async def mailing_loop(bot: Bot):
    while True:
        try:
            await process_mailings(bot)
            await check_new_orders(bot)
        except Exception as e:
            logger.error("Mailing loop error: %s", e)
        await asyncio.sleep(60)


async def main():
    await init_db()

    proxy_url = await get_proxy_url()

    if proxy_url:
        logger.info("Using proxy: %s", proxy_url)
        timeout = aiohttp.ClientTimeout(total=300, connect=30)
        session = AiohttpSession(proxy=proxy_url, timeout=timeout)
        bot = Bot(token=TELEGRAM_BOT_TOKEN, session=session)
    else:
        logger.info("No proxy configured")
        bot = Bot(token=TELEGRAM_BOT_TOKEN)

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    scheduler = AsyncIOScheduler()
    scheduler.start()
    dp['scheduler'] = scheduler
    dp['bot'] = bot

    dp.update.middleware(DbMiddleware())
    register_handlers(dp)

    asyncio.create_task(mailing_loop(bot))

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
