import httpx
from shared.config import TELEGRAM_BOT_TOKEN

API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def send_message(chat_id: int, text: str) -> bool:
    """Отправляет текстовое сообщение пользователю в Telegram."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        )
        return resp.status_code == 200


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
