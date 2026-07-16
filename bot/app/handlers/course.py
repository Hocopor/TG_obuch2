import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User
from shared.database import async_session
from shared.funnel import advance_stage
from ..services.delayed import run_detached
from ..services.app_settings import get_tariff_urls
from ..keyboards import tariff_msg_kb, tariff_final_kb, learn_tariffs_kb

router = Router()

TARIFF_SELF_TEXT = (
    "💎 Самостоятельный — 7 900 ₽\n\n"
    "• Срок доступа: 6 месяцев.\n"
    "• Полный курс: 4 модуля, 14 уроков.\n"
    "• Библиотека промптов.\n"
    "• Чек-лист брифа для общения с клиентом.\n"
    "• Таблица расчёта себестоимости ролика.\n"
    "• Примеры готовых сценариев.\n"
    "• PDF и дополнительные материалы.\n"
    "• Ссылки на используемые сервисы.\n"
    "• Обновления курса в течение срока доступа."
)

TARIFF_SUPPORT_TEXT = (
    "🛡 С поддержкой — 10 900 ₽\n\n"
    "• Срок доступа: 12 месяцев.\n"
    "• Всё из тарифа «Самостоятельный».\n"
    "• Закрытый Telegram-чат.\n"
    "• Поддержка наставников 60 дней.\n"
    "• Ответы на вопросы по урокам, нейросетям, генерации и монтажу.\n"
    "• Проверка одного итогового ролика с рекомендациями.\n"
    "• Короткие дополнительные уроки и обзоры новых сервисов."
)

TARIFF_PRO_TEXT = (
    "🚀 PRO — Первый коммерческий проект — 14 900 ₽\n\n"
    "• Срок доступа: 12 месяцев.\n"
    "• Всё из тарифа «С поддержкой».\n"
    "• Один реальный объект недвижимости из одобренной базы.\n"
    "• Контакт с настоящим собственником или риелтором.\n"
    "• Первый коммерческий проект для портфолио.\n"
    "• Проверка ролика перед передачей заказчику.\n"
    "• Возможность получить отзыв.\n"
    "• Возможность продолжить сотрудничество с заказчиком напрямую.\n"
    "• Расходы на генерации заказчик оплачивает ученику напрямую."
)


@router.callback_query(F.data == "course_detail")
async def course_detail(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    from .menu import ABOUT_COURSE_TEXT
    tg_id = callback.from_user.id
    await bot.send_message(tg_id, ABOUT_COURSE_TEXT)
    run_detached(_send_program_then_tariffs(bot, tg_id))


async def _send_program_then_tariffs(bot: Bot, tg_id: int):
    from .menu import PROGRAM_TEXT
    await asyncio.sleep(15)
    await bot.send_message(tg_id, PROGRAM_TEXT, reply_markup=learn_tariffs_kb())
    async with async_session() as s:
        u = (await s.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
        if u:
            advance_stage(u, "course_detail")
            await s.commit()


@router.callback_query(F.data == "compare_tariffs")
async def compare_tariffs(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    await callback.answer()
    urls = await get_tariff_urls(session)
    tg_id = callback.from_user.id
    run_detached(_send_tariffs(bot, tg_id, urls))


async def _send_tariffs(bot: Bot, tg_id: int, urls: dict):
    from ..services.cache import send_cached_photo
    await bot.send_message(tg_id, TARIFF_SELF_TEXT, reply_markup=tariff_msg_kb(urls["self"], "7 900"))
    await bot.send_message(tg_id, TARIFF_SUPPORT_TEXT, reply_markup=tariff_msg_kb(urls["support"], "10 900"))
    await bot.send_message(tg_id, TARIFF_PRO_TEXT, reply_markup=tariff_msg_kb(urls["pro"], "14 900"))
    await send_cached_photo(bot, tg_id, "files/images/сравнительнаятаблица.png", "📊 Сравнение тарифов:")
    await bot.send_message(tg_id, "Выберите тариф:", reply_markup=tariff_final_kb(urls))
    async with async_session() as s:
        u = (await s.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
        if u:
            advance_stage(u, "tariffs_viewed")
            await s.commit()
