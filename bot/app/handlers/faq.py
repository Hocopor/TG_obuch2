from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from ..keyboards import main_menu_kb

router = Router()

FAQ_TEXT = (
    "Частые вопросы:\n"
    "Сколько вам лет? - 20\n"
    "Вы женаты? - Да\n"
    "Есть ли на свете рай? - Да. Это Краснодарский край."
)


@router.message(F.text == "Частые вопросы")
async def faq_text(message: Message):
    await message.answer(FAQ_TEXT, reply_markup=main_menu_kb())


@router.callback_query(F.data == "faq")
async def faq_callback(callback: CallbackQuery):
    await callback.message.answer(FAQ_TEXT, reply_markup=main_menu_kb())
    await callback.answer()
