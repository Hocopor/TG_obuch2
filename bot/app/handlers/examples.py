import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile

from ..keyboards import after_examples_kb

router = Router()


async def send_examples(message: Message, bot=None):
    videos = [
        ("files/video/видео_пример_1.mov", "🔥 Набрал 300000 просмотров", 5),
        ("files/video/видео_пример_2.mov", "🔥 Набрал 350000 просмотров", 20),
        ("files/video/видео_пример_3.mov", "🔥 Набрал 325000 просмотров", 20),
    ]

    for path, caption, delay in videos:
        await asyncio.sleep(delay)
        await message.answer_video(
            video=FSInputFile(path),
            caption=caption
        )

    await asyncio.sleep(3)
    await message.answer(
        "🎁 Хочешь так же? Держи 4 бесплатных урока!",
        reply_markup=after_examples_kb()
    )


@router.message(F.text.contains("Примеры работ"))
async def examples_text(message: Message):
    await send_examples(message)


@router.callback_query(F.data == "examples")
async def examples_callback(callback: CallbackQuery):
    await send_examples(callback.message)
    await callback.answer()
