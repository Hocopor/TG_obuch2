import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from shared.config import TELEGRAM_BOT_TOKEN
from shared.database import init_db
from .handlers import register_handlers
from .middlewares import DbMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
