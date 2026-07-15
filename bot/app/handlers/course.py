from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User
from ..keyboards import tariff_select_kb, main_menu_kb

router = Router()

COURSE_DETAIL_TEXT = (
    "Подробное описание курса «ИИ для упаковки недвижимости»:\n\n"
    "Курс создан для тех, кто хочет научиться создавать продающие видео "
    "для объектов недвижимости с помощью нейросетей.\n\n"
    "Что вас ждёт:\n"
    "• 4 модуля и 14 коротких уроков (от 2 до 9 минут каждый)\n"
    "• Пошаговые инструкции — смотрите и повторяете\n"
    "• Практика на реальных объектах\n"
    "• Группа поддержки на весь период обучения\n"
    "• Личное наставничество\n"
    "• Возможность получить реальные заказы\n\n"
    "Курс подходит как новичкам, так и опытным видеографам, "
    "которые хотят добавить AI-инструменты в свой арсенал."
)

TARIFF_SELF_TEXT = (
    "Тариф «Самостоятельный» — 7 900 ₽\n\n"
    "• Все 14 уроков курса\n"
    "• Доступ к материалам навсегда\n"
    "• Чек-листы и шаблоны\n"
    "• Бонусные материалы\n\n"
    "Подходит для тех, кто предпочитает учиться в своём темпе."
)

TARIFF_SUPPORT_TEXT = (
    "Тариф «С поддержкой» — 10 900 ₽\n\n"
    "• Всё из тарифа «Самостоятельный»\n"
    "• Группа поддержки на 3 месяца\n"
    "• Ответы на вопросы от преподавателя\n"
    "• Разбор ваших работ\n\n"
    "Подходит для тех, кто хочет получать обратную связь."
)

TARIFF_PRO_TEXT = (
    "Тариф «PRO» — 14 900 ₽\n\n"
    "• Всё из тарифа «С поддержкой»\n"
    "• Личное наставничество\n"
    "• Сопровождение на протяжении обучения\n"
    "• Возможность получить реальные заказы от наших заказчиков\n"
    "• Помощь в построении карьеры\n\n"
    "Максимальный результат для тех, кто готов к серьёзным изменениям."
)


@router.callback_query(F.data == "course_detail")
async def course_detail(callback: CallbackQuery):
    await callback.message.answer(COURSE_DETAIL_TEXT, reply_markup=tariff_select_kb())
    await callback.answer()


@router.callback_query(F.data == "compare_tariffs")
async def compare_tariffs(callback: CallbackQuery):
    await callback.message.answer(TARIFF_SELF_TEXT)
    from asyncio import sleep
    await sleep(1)
    await callback.message.answer(TARIFF_SUPPORT_TEXT)
    await sleep(1)
    await callback.message.answer(TARIFF_PRO_TEXT)

    await callback.message.answer_photo(
        photo=InputFile("files/images/сравнительнаятаблица.png"),
        reply_markup=tariff_select_kb()
    )
    await callback.answer()


@router.message(F.text == "Узнать тарифы")
async def learn_tariffs(message: Message):
    await message.answer(TARIFF_SELF_TEXT)
    from asyncio import sleep
    await sleep(1)
    await message.answer(TARIFF_SUPPORT_TEXT)
    await sleep(1)
    await message.answer(TARIFF_PRO_TEXT)

    await message.answer_photo(
        photo=InputFile("files/images/сравнительнаятаблица.png"),
        reply_markup=tariff_select_kb()
    )
