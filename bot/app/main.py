import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from shared.config import TELEGRAM_BOT_TOKEN
from shared.database import init_db
from .handlers import register_handlers
from .middlewares import DbMiddleware
from .services.mailing import process_mailings, check_new_orders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
