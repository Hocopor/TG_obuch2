import os
import logging
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from aiogram import Bot
from aiogram.types import FSInputFile
from shared.models import CachedFile
from shared.database import async_session

logger = logging.getLogger(__name__)


def _mtime(file_path: str):
    try:
        return os.path.getmtime(file_path)
    except OSError:
        return None


async def get_cached_file(file_path: str, mtime) -> str | None:
    """Вернуть file_id, только если mtime в БД совпадает с текущим (иначе файл заменён — перезалить)."""
    if mtime is None:
        return None
    async with async_session() as session:
        result = await session.execute(
            select(CachedFile).where(CachedFile.file_path == file_path)
        )
        cached = result.scalar_one_or_none()
        if cached and cached.file_mtime == mtime:
            return cached.file_id
        return None


async def save_cached_file(file_path: str, file_id: str, file_type: str, mtime):
    """Upsert по file_path (ON CONFLICT DO UPDATE) — гасит гонку двух пользователей на холодном кэше."""
    if mtime is None:
        return
    async with async_session() as session:
        stmt = pg_insert(CachedFile).values(
            file_path=file_path, file_id=file_id, file_type=file_type, file_mtime=mtime,
        ).on_conflict_do_update(
            index_elements=["file_path"],
            set_={"file_id": file_id, "file_type": file_type, "file_mtime": mtime},
        )
        await session.execute(stmt)
        await session.commit()


async def send_cached_video(bot: Bot, chat_id: int, file_path: str, caption: str = "", reply_markup=None):
    mtime = _mtime(file_path)
    cached_id = await get_cached_file(file_path, mtime)
    if cached_id:
        try:
            await bot.send_video(chat_id=chat_id, video=cached_id, caption=caption, reply_markup=reply_markup)
            return
        except Exception:
            pass
    file = FSInputFile(file_path)
    msg = await bot.send_video(chat_id=chat_id, video=file, caption=caption, reply_markup=reply_markup)
    if msg.video:
        await save_cached_file(file_path, msg.video.file_id, "video", mtime)


async def send_cached_photo(bot: Bot, chat_id: int, file_path: str, caption: str = "", reply_markup=None):
    mtime = _mtime(file_path)
    cached_id = await get_cached_file(file_path, mtime)
    if cached_id:
        try:
            await bot.send_photo(chat_id=chat_id, photo=cached_id, caption=caption, reply_markup=reply_markup)
            return
        except Exception:
            pass
    file = FSInputFile(file_path)
    msg = await bot.send_photo(chat_id=chat_id, photo=file, caption=caption, reply_markup=reply_markup)
    if msg.photo:
        await save_cached_file(file_path, msg.photo[-1].file_id, "photo", mtime)
