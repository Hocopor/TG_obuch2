from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from ..keyboards import after_examples_kb

router = Router()


async def send_menu_examples(bot: Bot, chat_id: int):
    from ..services.cache import send_cached_video
    videos = [
        ("files/video/видео_пример_1.mp4", "🔥 Набрал 300000 просмотров"),
        ("files/video/видео_пример_2.mp4", "🔥 Набрал 350000 просмотров"),
        ("files/video/видео_пример_3.mp4", "🔥 Набрал 325000 просмотров"),
    ]
    for path, caption in videos:
        await send_cached_video(bot, chat_id, path, caption)
    await bot.send_message(
        chat_id,
        "🎬 Понравились примеры? Записывайтесь на курс — научитесь так же!",
        reply_markup=after_examples_kb(),
    )
