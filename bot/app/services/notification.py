import logging
from aiogram import Bot

from shared.models import User, Object

logger = logging.getLogger(__name__)


async def notify_object_assigned(bot: Bot, obj: Object, user: User):
    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=(
                f"Вам назначен объект «{obj.object_name}».\n"
                f"Адрес: {obj.address or 'не указан'}\n"
                f"Описание: {obj.description or 'не указано'}"
            ),
        )
    except Exception as e:
        logger.warning("Failed to notify user %d about object %d: %s", user.id, obj.id, e)
