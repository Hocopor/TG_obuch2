import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))
DB_USER = os.getenv("DB_USER", "tg_bot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
ADMINKA_URL = os.getenv("ADMINKA_URL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# Fail-fast: обязательные переменные окружения (A4)
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не задана обязательная переменная окружения TELEGRAM_BOT_TOKEN")
if not CHAT_ID:
    raise RuntimeError("Не задана обязательная переменная окружения CHAT_ID")

# Экранирование логина/пароля в DSN (A3)
_user = quote_plus(DB_USER)
_pwd = quote_plus(DB_PASSWORD)
DB_URL = f"postgresql+asyncpg://{_user}:{_pwd}@db:5432/tg_bot"
DB_URL_SYNC = f"postgresql://{_user}:{_pwd}@db:5432/tg_bot"

from zoneinfo import ZoneInfo
TZ = ZoneInfo("Europe/Moscow")
