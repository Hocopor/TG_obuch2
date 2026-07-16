import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User
from shared.config import CHAT_ID

logger = logging.getLogger(__name__)

_locks: dict[int, asyncio.Lock] = {}


def _get_lock(tg_id: int) -> asyncio.Lock:
    lock = _locks.get(tg_id)
    if lock is None:
        lock = asyncio.Lock()
        _locks[tg_id] = lock
    return lock


def _topic_name(user: User) -> str:
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    handle = f"@{user.username}" if user.username else f"id{user.telegram_id}"
    full = f"{name} ({handle} / {user.telegram_id})".strip()
    if len(full) > 128:
        full = full[:125] + "..."
    return full


async def ensure_thread(bot: Bot, session: AsyncSession, user: User) -> int:
    """Возвращает support_thread_id пользователя; создаёт тему, если её нет. Гонку двух тем гасит per-user Lock."""
    if user.support_thread_id:
        return user.support_thread_id
    async with _get_lock(user.telegram_id):
        await session.refresh(user)
        if user.support_thread_id:
            return user.support_thread_id
        topic = await bot.create_forum_topic(chat_id=CHAT_ID, name=_topic_name(user))
        user.support_thread_id = topic.message_thread_id
        await session.commit()
        return user.support_thread_id


def _thread_gone(e: Exception) -> bool:
    t = str(e).lower()
    return any(s in t for s in ("thread not found", "topic_closed", "topic closed", "message thread not found"))


async def _deliver(bot: Bot, session: AsyncSession, user: User, action) -> bool:
    """action: async callable(thread_id) -> Any. При закрытой/удалённой теме пересоздаёт и повторяет один раз."""
    thread = await ensure_thread(bot, session, user)
    try:
        await action(thread)
        return True
    except TelegramBadRequest as e:
        if _thread_gone(e):
            user.support_thread_id = None
            await session.commit()
            thread = await ensure_thread(bot, session, user)
            try:
                await action(thread)
                return True
            except Exception as e2:
                logger.warning("deliver retry failed: %s", e2)
                return False
        logger.warning("deliver failed: %s", e)
        return False
    except Exception as e:
        logger.warning("deliver failed: %s", e)
        return False


async def deliver_to_support(bot: Bot, session: AsyncSession, user: User, message: Message) -> bool:
    """Пересылает произвольное сообщение пользователя в его тему (copy_to — работает для любого типа)."""
    return await _deliver(bot, session, user, lambda t: message.copy_to(chat_id=CHAT_ID, message_thread_id=t))


async def deliver_text_to_support(bot: Bot, session: AsyncSession, user: User, text: str) -> bool:
    """Отправляет текст (вопрос из кнопочного флоу) в тему пользователя."""
    return await _deliver(bot, session, user, lambda t: bot.send_message(chat_id=CHAT_ID, message_thread_id=t, text=text))
