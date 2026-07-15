import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..keyboards import course_detail_kb

router = Router()


async def send_reviews(message: Message, session: AsyncSession = None, bot=None):
    await message.answer(
        "Наше обучение прошли уже 250 человек, и вот, что они говорят по итогу обучения"
    )

    await asyncio.sleep(3)
    await message.answer_photo(
        photo=InputFile("files/images/отзыв_анна.jpg"),
        caption=(
            "Анна, Москва, домохозяйка, спустя месяц после обучения "
            "доход на видосиках 100к в месяц."
        )
    )

    await asyncio.sleep(5)
    await message.answer_photo(
        photo=InputFile("files/images/отзыв_владимир.jpg"),
        caption=(
            "Владимир, Краснодар, безработный, спустя месяц после обучения, "
            "доход от продажи своих объектов, для которых он сделал эти видосики - "
            "100500 руб в месяц"
        )
    )

    await asyncio.sleep(15)
    await message.answer(
        "На данный момент мы сделали более 150 заказов для наших клиентов, "
        "и этот список постоянно пополняется!",
        reply_markup=course_detail_kb()
    )


@router.message(F.text == "Отзывы")
async def reviews_text(message: Message, session: AsyncSession):
    await send_reviews(message, session)


@router.callback_query(F.data == "reviews")
async def reviews_callback(callback: CallbackQuery, session: AsyncSession):
    await send_reviews(callback.message, session)
    await callback.answer()
