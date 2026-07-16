import logging
import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from shared.models import User

logger = logging.getLogger(__name__)

# Разрешено без согласий
ALLOWED_CALLBACKS = {"accept_all", "noop"}

_last_prompt: Dict[int, float] = {}
PROMPT_INTERVAL = 15  # сек — не чаще одного консент-экрана


def _is_start_command(text: str | None) -> bool:
    if not text:
        return False
    first = text.split()[0].split("@")[0]
    return first == "/start"


class ConsentMiddleware(BaseMiddleware):
    """Блокирует бота, пока пользователь не принял обе политики."""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Только приватные чаты; группы (поддержка) пропускаем
        if isinstance(event, Message):
            chat = event.chat
        else:
            if event.message is None:
                return await handler(event, data)
            chat = event.message.chat
        if chat.type != "private":
            return await handler(event, data)

        session = data.get("session")
        if session is None:
            return await handler(event, data)

        user_id = event.from_user.id
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()

        # Есть оба согласия — пропускаем
        if user and user.consent_offer and user.consent_personal_data:
            return await handler(event, data)

        # Разрешённые действия без согласий
        if isinstance(event, CallbackQuery):
            if event.data in ALLOWED_CALLBACKS:
                return await handler(event, data)
        else:
            if _is_start_command(event.text):
                return await handler(event, data)

        # Блокируем — показываем консент-экран (анти-спам 15 сек)
        now = time.monotonic()
        if now - _last_prompt.get(user_id, 0.0) < PROMPT_INTERVAL:
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer()
                except Exception:
                    pass
            return None
        _last_prompt[user_id] = now

        from ..services.legal import get_legal_links
        offer_url, privacy_url, pd_url = await get_legal_links(session)
        from ..keyboards import consent_kb
        from ..handlers.start import get_consent_text
        text = get_consent_text(offer_url, privacy_url, pd_url)

        try:
            if isinstance(event, CallbackQuery):
                await event.message.answer(text, reply_markup=consent_kb(), parse_mode="Markdown")
                await event.answer()
            else:
                await event.answer(text, reply_markup=consent_kb(), parse_mode="Markdown")
        except Exception as e:
            logger.warning("ConsentMiddleware: failed to send consent prompt: %s", e)
        return None
