import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from sqlalchemy import select

from shared.database import async_session
from shared.models import User, AnalyticsEvent
from shared.funnel import advance_stage, STAGE_ORDER
from ..services.delayed import run_detached
from ..keyboards import course_detail_kb, home_kb

router = Router()

REVIEW_1 = (
    "👩 Анна, Москва, домохозяйка\n"
    "Спустя месяц после обучения доход на видосиках 100к в месяц."
)
REVIEW_2 = (
    "👨 Владимир, Краснодар, безработный\n"
    "Спустя месяц после обучения доход от продажи своих объектов, "
    "для которых он сделал эти видосики — 100500 руб в месяц."
)


async def send_menu_reviews(bot: Bot, chat_id: int):
    """Раздел меню «Отзывы» — только два отзыва + кнопка домой (по ТЗ)."""
    from ..services.cache import send_cached_photo
    await send_cached_photo(bot, chat_id, "files/images/отзыв_анна.jpg", REVIEW_1)
    await asyncio.sleep(5)
    await send_cached_photo(bot, chat_id, "files/images/отзыв_владимир.jpg", REVIEW_2, reply_markup=home_kb())


async def send_funnel_reviews(bot: Bot, tg_id: int):
    """Воронковая цепочка отзывов. Идемпотентна: второй запуск (таймер+кнопка+дабл-клик) выходит."""
    from ..services.cache import send_cached_photo
    async with async_session() as s:
        user = (await s.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
        if not user:
            return
        # уже отправляли — выходим
        if user.funnel_stage in STAGE_ORDER and STAGE_ORDER.index(user.funnel_stage) >= STAGE_ORDER.index("watched_lessons"):
            return
        advance_stage(user, "watched_lessons")
        s.add(AnalyticsEvent(user_id=user.id, event_type="watched_lessons"))
        await s.commit()

    await bot.send_message(
        tg_id,
        "💬 Наше обучение прошли уже 250 человек, и вот, что они говорят по итогу обучения:"
    )
    await asyncio.sleep(3)
    await send_cached_photo(bot, tg_id, "files/images/отзыв_анна.jpg", REVIEW_1)
    await asyncio.sleep(5)
    await send_cached_photo(bot, tg_id, "files/images/отзыв_владимир.jpg", REVIEW_2)
    await asyncio.sleep(15)
    await bot.send_message(
        tg_id,
        "📦 150 заказов. Ровно столько нам пришло в этом месяце заказов, "
        "и мы не смогли их отработать из-за нехватки времени.\n\n"
        "Эти заказы могли бы попасть к вам...\n"
        "Спрос выше предложения.\n\n"
        "🚀 Используйте возможность зайти в самое подходящее время, "
        "и занять своё место в этой нише.\n"
        "Через год войти будет сложнее.\n"
        "Будьте в числе первых!",
        reply_markup=course_detail_kb(),
    )


@router.callback_query(F.data == "reviews")
async def reviews_callback(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    run_detached(send_menu_reviews(bot, callback.from_user.id))
