from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User
from shared.config import CHAT_ID

router = Router()


@router.message(F.chat.id == CHAT_ID)
async def support_message(message: Message, session: AsyncSession):
    if not message.message_thread_id:
        return

    result = await session.execute(
        select(User).where(User.support_thread_id == message.message_thread_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    if message.from_user and message.from_user.id == message.bot.id:
        return

    try:
        if message.text:
            await message.bot.send_message(
                chat_id=user.telegram_id,
                text=message.text
            )
        elif message.photo:
            await message.bot.send_photo(
                chat_id=user.telegram_id,
                photo=message.photo[-1].file_id,
                caption=message.caption or ""
            )
        elif message.video:
            await message.bot.send_video(
                chat_id=user.telegram_id,
                video=message.video.file_id,
                caption=message.caption or ""
            )
        elif message.document:
            await message.bot.send_document(
                chat_id=user.telegram_id,
                document=message.document.file_id,
                caption=message.caption or ""
            )
    except Exception:
        pass
