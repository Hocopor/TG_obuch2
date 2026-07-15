import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from shared.models import User
from shared.database import async_session

logger = logging.getLogger(__name__)

# Callback_data, которые разрешены без согласий
ALLOWED_CALLBACKS = {
    "accept_offer", "accept_pd", "noop", "start",
}

# Команды, которые разрешены без согласий
ALLOWED_COMMANDS = {"/start"}


class ConsentMiddleware(BaseMiddleware):
    """Блокирует взаимодействие с ботом, пока пользователь не примет обе политики."""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем группы
        chat = event.chat if isinstance(event, Message) else event.message.chat
        if chat.type != "private":
            return await handler(event, data)

        user_id = event.from_user.id

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()

        # Новый пользователь — пропускаем (start создаст запись)
        if not user:
            return await handler(event, data)

        # Уже принял обе политики — пропускаем
        if user.consent_offer and user.consent_personal_data:
            return await handler(event, data)

        # Разрешённые действия без согласий
        if isinstance(event, CallbackQuery):
            if event.data in ALLOWED_CALLBACKS:
                return await handler(event, data)
        elif isinstance(event, Message):
            if event.text and event.text.split()[0] in ALLOWED_COMMANDS:
                return await handler(event, data)

        # Блокируем — показываем экран согласия
        async with async_session() as session:
            from ..services.legal import get_legal_links
            offer_url, privacy_url, pd_url = await get_legal_links(session)

        if not user.consent_offer:
            from ..keyboards import consent_offer_kb
            text = (
                "👋 Для продолжения необходимо принять условия:\n\n"
                f"📄 [Оферта]({offer_url})\n"
                f"🔒 [Политика конфиденциальности]({privacy_url})\n\n"
                "Нажмите кнопку ниже, чтобы принять:"
            )
            kb = consent_offer_kb()
        else:
            from ..keyboards import consent_pd_kb
            text = (
                "🔒 Также необходимо принять:\n\n"
                f"📄 [Политика персональных данных]({pd_url})\n\n"
                "Нажмите кнопку ниже, чтобы принять:"
            )
            kb = consent_pd_kb()

        try:
            if isinstance(event, CallbackQuery):
                await event.message.answer(text, reply_markup=kb, parse_mode="Markdown")
                await event.answer()
            else:
                await event.answer(text, reply_markup=kb, parse_mode="Markdown")
        except Exception as e:
            logger.warning("ConsentMiddleware: failed to send consent prompt: %s", e)

        return None
