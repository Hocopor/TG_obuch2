from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User
from ..keyboards import main_menu_kb, tariff_select_kb, about_course_kb, program_kb
from ..services.legal import get_free_lessons_link

router = Router()

ABOUT_COURSE_TEXT = (
    "«ИИ для упаковки недвижимости» — пошаговый практический курс по созданию "
    "продающих AI-роликов для объектов недвижимости. Курс состоит из 4 модулей "
    "и 14 коротких уроков в записи. Продолжительность одного урока — от 2 до 9 минут. "
    "Материал разбит на небольшие шаги, чтобы Вы могли посмотреть урок и сразу "
    "повторить действия на своём объекте. Кроме того, вы получаете группу поддержки "
    "на весь период обучения, личное наставничество и возможность получить реальный заказ "
    "от наших заказчиков, уже в процессе обучения."
)

PROGRAM_TEXT = (
    "Программа курса:\n\n"
    "Модуль 1. Введение в AI-видео для недвижимости\n"
    "• Урок 1. Обзор инструментов и платформ (3 мин)\n"
    "• Урок 2. Подготовка материалов: фото и видео объекта (4 мин)\n"
    "• Урок 3. Первый AI-ролик за 15 минут (5 мин)\n"
    "• Урок 4. Настройка качества и результата (3 мин)\n\n"
    "Модуль 2. Продвинутые техники монтажа\n"
    "• Урок 5. Работа со звуком и музыкой (4 мин)\n"
    "• Урок 6. Титры, переходы и эффекты (5 мин)\n"
    "• Урок 7. Создание серии видео для одного объекта (6 мин)\n\n"
    "Модуль 3. Монетизация и продажи\n"
    "• Урок 8. Формирование портфолио (3 мин)\n"
    "• Урок 9. Поиск клиентов: риелторы и застройщики (5 мин)\n"
    "• Урок 10. Ценообразование и заключение сделок (4 мин)\n\n"
    "Модуль 4. Масштабирование\n"
    "• Урок 11. Автоматизация процессов (6 мин)\n"
    "• Урок 12. Работа с несколькими объектами одновременно (5 мин)\n"
    "• Урок 13. Создание自己的 стиля и бренда (4 мин)\n"
    "• Урок 14. План развития на 3 месяца (2 мин)\n\n"
    "Бонусы:\n"
    "• Шаблоны продающих писем для рассылки риелторам\n"
    "• Чек-лист подготовки объекта к съёмке\n"
    "• Доступ в группу поддержки на 3 месяца"
)


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    await callback.message.answer("Главное меню", reply_markup=main_menu_kb())
    await callback.answer()


@router.message(F.text == "Главное меню")
async def main_menu_text(message: Message):
    await message.answer("Главное меню", reply_markup=main_menu_kb())


@router.message(F.text == "Бесплатные материалы")
async def free_materials(message: Message, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.funnel_stage = "free_materials_viewed"
        await session.commit()

    free_lessons_url = await get_free_lessons_link(session)
    if free_lessons_url:
        text = f"Вот ваши бесплатные материалы:\n[Открыть]({free_lessons_url})"
        await message.answer(text, reply_markup=main_menu_kb(), parse_mode="Markdown")
    else:
        await message.answer(
            "Вот ваши бесплатные материалы: #free_lessons",
            reply_markup=main_menu_kb()
        )


@router.message(F.text == "Записаться на курс")
async def enroll_text(message: Message):
    await message.answer("Выберите тариф", reply_markup=tariff_select_kb())


@router.callback_query(F.data == "enroll")
async def enroll_callback(callback: CallbackQuery):
    await callback.message.answer("Выберите тариф", reply_markup=tariff_select_kb())
    await callback.answer()


@router.message(F.text == "О курсе")
async def about_course(message: Message):
    await message.answer(ABOUT_COURSE_TEXT, reply_markup=about_course_kb())


@router.message(F.text == "Программа")
async def program(message: Message):
    await message.answer(PROGRAM_TEXT, reply_markup=program_kb())


@router.callback_query(F.data == "program")
async def program_callback(callback: CallbackQuery):
    await callback.message.answer(PROGRAM_TEXT, reply_markup=program_kb())
    await callback.answer()
