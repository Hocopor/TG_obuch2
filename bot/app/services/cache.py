import logging
from sqlalchemy import select
from aiogram import Bot
from aiogram.types import FSInputFile
from shared.models import CachedFile
from shared.database import async_session

logger = logging.getLogger(__name__)


async def get_cached_file(file_path: str) -> str | None:
    async with async_session() as session:
        result = await session.execute(
            select(CachedFile).where(CachedFile.file_path == file_path)
        )
        cached = result.scalar_one_or_none()
        return cached.file_id if cached else None


async def save_cached_file(file_path: str, file_id: str, file_type: str):
    async with async_session() as session:
        result = await session.execute(
            select(CachedFile).where(CachedFile.file_path == file_path)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.file_id = file_id
        else:
            session.add(CachedFile(
                file_path=file_path,
                file_id=file_id,
                file_type=file_type,
            ))
        await session.commit()


async def send_cached_video(bot: Bot, chat_id: int, file_path: str, caption: str = "", reply_markup=None):
    cached_id = await get_cached_file(file_path)
    if cached_id:
        try:
            await bot.send_video(chat_id=chat_id, video=cached_id, caption=caption, reply_markup=reply_markup)
            return
        except Exception:
            pass
    file = FSInputFile(file_path)
    msg = await bot.send_video(chat_id=chat_id, video=file, caption=caption, reply_markup=reply_markup)
    if msg.video:
        await save_cached_file(file_path, msg.video.file_id, "video")


async def send_cached_photo(bot: Bot, chat_id: int, file_path: str, caption: str = "", reply_markup=None):
    cached_id = await get_cached_file(file_path)
    if cached_id:
        try:
            await bot.send_photo(chat_id=chat_id, photo=cached_id, caption=caption, reply_markup=reply_markup)
            return
        except Exception:
            pass
    file = FSInputFile(file_path)
    msg = await bot.send_photo(chat_id=chat_id, photo=file, caption=caption, reply_markup=reply_markup)
    if msg.photo:
        await save_cached_file(file_path, msg.photo[-1].file_id, "photo")
