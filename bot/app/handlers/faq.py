from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from ..keyboards import home_kb

router = Router()

FAQ_TEXT = (
    "❓ Частые вопросы:\n\n"
    "👤 Сколько вам лет?\n"
    "— 20\n\n"
    "💍 Вы женаты?\n"
    "— Да\n\n"
    "🏖 Есть ли на свете рай?\n"
    "— Да. Это Краснодарский край."
)


@router.callback_query(F.data == "faq")
async def faq_callback(callback: CallbackQuery):
    await callback.message.answer(FAQ_TEXT, reply_markup=home_kb())
    await callback.answer()
