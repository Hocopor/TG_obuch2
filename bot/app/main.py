import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, text
from shared.config import TELEGRAM_BOT_TOKEN, ADMINKA_URL
from shared.database import async_session
from shared.models import Settings
from .handlers import register_handlers
from .middlewares import DbMiddleware, ConsentMiddleware
from .services.mailing import process_mailings

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


async def proxy_watcher(bot: Bot, current_proxy: str, interval: int = 10):
    """Подхватывает смену прокси из админки без рестарта бота.

    Раз в `interval` секунд читает proxy_url из БД; при изменении пересобирает
    bot.session на лету (новый AiohttpSession с новым/без прокси) и закрывает старую.
    Висящий long-poll на старой сессии оборвётся — polling-цикл aiogram сам
    переподключится уже через новую сессию.
    """
    while True:
        await asyncio.sleep(interval)
        try:
            new_proxy = await get_proxy_url()
        except Exception as e:
            logger.error("proxy_watcher: не смог прочитать прокси из БД: %s", e)
            continue
        if new_proxy == current_proxy:
            continue

        logger.info("Прокси изменён (%r -> %r) — пересобираю сессию бота", current_proxy, new_proxy)
        old_session = bot.session
        try:
            if new_proxy:
                bot.session = AiohttpSession(proxy=new_proxy, timeout=300)
            else:
                bot.session = AiohttpSession(timeout=300)
        except Exception as e:
            logger.error("proxy_watcher: не смог создать новую сессию (%r): %s", new_proxy, e)
            continue
        current_proxy = new_proxy

        try:
            await old_session.close()
        except Exception:
            pass


async def mailing_loop(bot: Bot):
    while True:
        try:
            await process_mailings(bot)
        except Exception as e:
            logger.error("Mailing loop error: %s", e)
        await asyncio.sleep(60)


async def wait_for_db(max_wait: int = 60):
    """Ждёт, пока admin создаст таблицы (create_all делает только admin)."""
    import time
    start = time.monotonic()
    while True:
        try:
            async with async_session() as session:
                await session.execute(text("SELECT 1 FROM users LIMIT 1"))
            logger.info("DB is ready")
            return
        except Exception as e:
            if time.monotonic() - start > max_wait:
                raise RuntimeError(
                    f"БД не инициализирована за {max_wait} сек (таблицы должен создать admin). Последняя ошибка: {e}"
                )
            logger.info("Waiting for DB to be initialized by admin...")
            await asyncio.sleep(2)


async def main():
    if not ADMINKA_URL:
        raise RuntimeError("Не задана обязательная переменная окружения ADMINKA_URL")
    await wait_for_db()

    proxy_url = await get_proxy_url()

    if proxy_url:
        logger.info("Using proxy: %s", proxy_url)
        session = AiohttpSession(proxy=proxy_url, timeout=300)
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
    dp.message.middleware(ConsentMiddleware())
    dp.callback_query.middleware(ConsentMiddleware())
    register_handlers(dp)

    async with async_session() as s:
        await s.execute(text("UPDATE mailings SET status='pending' WHERE status='sending'"))
        await s.commit()

    mailing_task = asyncio.create_task(mailing_loop(bot))
    proxy_task = asyncio.create_task(proxy_watcher(bot, proxy_url))

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
