import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from ..keyboards import course_detail_kb

router = Router()


async def send_reviews(message: Message, session: AsyncSession = None, bot=None):
    from ..services.cache import send_cached_photo

    await message.answer(
        "💬 Наше обучение прошли уже 250 человек, и вот, что они говорят по итогу обучения:"
    )

    await asyncio.sleep(3)
    await send_cached_photo(
        message.bot, message.chat.id,
        "files/images/отзыв_анна.jpg",
        "👩 Анна, Москва, домохозяйка\n"
        "Спустя месяц после обучения доход на видосиках 100к в месяц."
    )

    await asyncio.sleep(5)
    await send_cached_photo(
        message.bot, message.chat.id,
        "files/images/отзыв_владимир.jpg",
        "👨 Владимир, Краснодар, безработный\n"
        "Спустя месяц после обучения доход от продажи своих объектов, "
        "для которых он сделал эти видосики — 100500 руб в месяц."
    )

    await asyncio.sleep(15)
    await message.answer(
        "📦 150 заказов. Ровно столько нам пришло в этом месяце заказов, "
        "и мы не смогли их отработать из-за нехватки времени.\n\n"
        "Эти заказы могли бы попасть к вам...\n"
        "Спрос выше предложения.\n\n"
        "🚀 Используйте возможность зайти в самое подходящее время, "
        "и занять своё место в этой нише.\n"
        "Через год войти будет сложнее.\n"
        "Будьте в числе первых!",
        reply_markup=course_detail_kb()
    )


@router.message(F.text.contains("Отзывы"))
async def reviews_text(message: Message, session: AsyncSession):
    await send_reviews(message, session)


@router.callback_query(F.data == "reviews")
async def reviews_callback(callback: CallbackQuery, session: AsyncSession):
    await send_reviews(callback.message, session)
    await callback.answer()
