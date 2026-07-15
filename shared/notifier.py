import logging
import httpx
from sqlalchemy import select
from shared.config import TELEGRAM_BOT_TOKEN
from shared.database import async_session
from shared.models import Settings

logger = logging.getLogger(__name__)

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def _get_proxy_url() -> str | None:
    """Получает URL прокси из БД."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Settings).where(Settings.key == "proxy_url")
            )
            setting = result.scalar_one_or_none()
            if setting and setting.value:
                return setting.value
    except Exception as e:
        logger.error("Failed to get proxy from DB: %s", e)
    return None


async def send_message(chat_id: int, text: str) -> bool:
    """Отправляет текстовое сообщение пользователю в Telegram."""
    proxy_url = await _get_proxy_url()
    logger.info("Notifier: sending to chat_id=%s, proxy=%s", chat_id, proxy_url)
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=15) as client:
            resp = await client.post(
                f"{API_URL}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
            if resp.status_code != 200:
                logger.error("Notifier: Telegram API error %s: %s", resp.status_code, resp.text)
                return False
            logger.info("Notifier: message sent to chat_id=%s", chat_id)
            return True
    except Exception as e:
        logger.error("Notifier: failed to send to chat_id=%s: %s", chat_id, e)
        return False


async def notify_customer(customer_telegram_id: int, object_name: str):
    """Уведомляет заказчика, что его объект принят в работу."""
    text = (
        f"🏠 <b>Ваш объект принят в работу!</b>\n\n"
        f"Объект: <b>{object_name}</b>\n"
        f"Мы уже приступили к работе. Скоро с вами свяжутся для уточнения деталей."
    )
    await send_message(customer_telegram_id, text)


async def notify_performer(
    performer_telegram_id: int,
    object_name: str,
    address: str,
    description: str,
    budget: str,
    customer_username: str,
):
    """Уведомляет исполнителя о назначении заказа."""
    text = (
        f"📌 <b>Вам назначен новый объект!</b>\n\n"
        f"Объект: <b>{object_name}</b>\n"
    )
    if address:
        text += f"Адрес: {address}\n"
    if description:
        text += f"Описание: {description}\n"
    if budget:
        text += f"Бюджет: {budget}\n"
    if customer_username:
        text += f"Заказчик: @{customer_username}\n"
    text += "\nСвяжитесь с заказчиком для обсуждения деталей."
    await send_message(performer_telegram_id, text)
