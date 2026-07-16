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
    if message.from_user and message.from_user.id == message.bot.id:
        return  # собственные пересланные сообщения бота не трогаем (иначе эхо-петля)

    result = await session.execute(
        select(User).where(User.support_thread_id == message.message_thread_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    try:
        await message.bot.copy_message(
            chat_id=user.telegram_id,
            from_chat_id=CHAT_ID,
            message_id=message.message_id,
        )
    except Exception as e:
        try:
            await message.reply(f"⚠️ Не доставлено пользователю: {e}")
        except Exception:
            pass
