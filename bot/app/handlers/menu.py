from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..keyboards import main_menu_kb, tariff_select_kb, about_course_kb, program_kb
from ..services.legal import get_free_lessons_link
from ..services.app_settings import get_tariff_urls
from ..services.delayed import run_detached

router = Router()

ABOUT_COURSE_TEXT = (
    "📚 «ИИ для упаковки недвижимости» — пошаговый практический курс по созданию "
    "продающих AI-роликов для объектов недвижимости.\n\n"
    "Курс состоит из 4 модулей и 14 коротких уроков в записи. "
    "Продолжительность одного урока — от 2 до 9 минут. "
    "Материал разбит на небольшие шаги, чтобы Вы могли посмотреть урок и сразу "
    "повторить действия на своём объекте.\n\n"
    "Кроме того, вы получаете:\n"
    "💬 Группу поддержки на весь период обучения\n"
    "👨‍🏫 Личное наставничество и сопровождение\n"
    "💼 Возможность получить реальный заказ от наших заказчиков, уже в процессе обучения."
)

PROGRAM_TEXT = (
    "📋 Программа курса:\n\n"
    "🎯 Модуль 1 — Старт\n"
    "• Обзор курса\n"
    "• База по нейросетям\n"
    "• Syntx. Обзор интерфейса\n"
    "• Основные этапы создания ролика\n\n"
    "🖥 Модуль 2 — Рабочее пространство\n"
    "• Рабочее пространство и минимальный набор\n"
    "• Доступ к зарубежным сервисам\n\n"
    "📦 Модуль 3 — Упаковка\n"
    "• Идея и хук\n"
    "• Сценарий\n"
    "• Себестоимость ролика\n\n"
    "🎬 Модуль 4 — Генерация\n"
    "• Раскадровка\n"
    "• Контроль над результатом\n"
    "• Анимация сцен\n"
    "• Монтаж\n\n"
    "🎁 Дополнительные материалы и бонусы:\n"
    "• Библиотека промптов\n"
    "• Чек-лист брифа\n"
    "• Таблица себестоимости\n"
    "• Примеры сценариев\n"
    "• Ссылки на сервисы\n"
    "• PDF-материалы"
)


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("🏠 Главное меню", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_free_materials")
async def menu_free_materials(callback: CallbackQuery, session: AsyncSession):
    free_lessons_url = await get_free_lessons_link(session)
    text = f"📚 Вот ваши бесплатные материалы:\n\n[Открыть уроки]({free_lessons_url})"
    await callback.message.answer(text, reply_markup=main_menu_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_enroll")
async def menu_enroll(callback: CallbackQuery, session: AsyncSession):
    urls = await get_tariff_urls(session)
    await callback.message.answer("🎓 Выберите тариф:", reply_markup=tariff_select_kb(urls))
    await callback.answer()


@router.callback_query(F.data == "menu_about")
async def menu_about(callback: CallbackQuery):
    await callback.message.answer(ABOUT_COURSE_TEXT, reply_markup=about_course_kb())
    await callback.answer()


@router.callback_query(F.data == "program")
async def program_callback(callback: CallbackQuery):
    await callback.message.answer(PROGRAM_TEXT, reply_markup=program_kb())
    await callback.answer()


@router.callback_query(F.data == "menu_examples")
async def menu_examples(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    from .examples import send_menu_examples
    run_detached(send_menu_examples(bot, callback.from_user.id))
