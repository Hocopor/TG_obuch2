from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Settings

DEFAULT_TARIFF_URLS = {
    "self": "https://getcourse.example.com/self",
    "support": "https://getcourse.example.com/support",
    "pro": "https://getcourse.example.com/pro",
}


async def get_setting(session: AsyncSession, key: str, default: str = "") -> str:
    result = await session.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        return setting.value
    return default


async def get_tariff_urls(session: AsyncSession) -> dict:
    return {
        "self": await get_setting(session, "tariff_self_url", DEFAULT_TARIFF_URLS["self"]),
        "support": await get_setting(session, "tariff_support_url", DEFAULT_TARIFF_URLS["support"]),
        "pro": await get_setting(session, "tariff_pro_url", DEFAULT_TARIFF_URLS["pro"]),
    }
