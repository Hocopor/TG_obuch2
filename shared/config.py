import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
ADMINKA_URL = os.getenv("ADMINKA_URL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

DB_URL = f"postgresql+asyncpg://tg_bot:{DB_PASSWORD}@db:5432/tg_bot"
DB_URL_SYNC = f"postgresql://tg_bot:{DB_PASSWORD}@db:5432/tg_bot"
