import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, ConsentLog, ConsentTypeEnum, GoalEnum, AnalyticsEvent
from shared.config import ADMINKA_URL
from ..keyboards import (
    consent_offer_kb, consent_offer_done_kb, consent_pd_kb, consent_pd_done_kb,
    next_kb, goal_kb, watched_kb, main_menu_kb
)
from ..services.legal import get_legal_links, get_free_lessons_link

router = Router()

WELCOME_TEXT = (
    "🎬 Хочешь научиться создавать крутые видео для объектов недвижимости "
    "с помощью ИИ, которые набирают миллионы просмотров?\n\n"
    "📚 Внутри бесплатные уроки, кейсы, и возможность записаться на обучение!\n\n"
    "👇 Используй возможность, жми /start"
)


def get_greeting_text(offer_url: str, privacy_url: str) -> str:
    return (
        "👋 Приветствуем в нашем боте!\n\n"
        "Согласно требований законодательства РФ, для продолжения, "
        "необходимо ознакомиться и принять:\n\n"
        f"📄 [Оферта]({offer_url})\n"
        f"🔒 [Политика конфиденциальности]({privacy_url})\n\n"
        "Нажмите кнопку ниже, чтобы принять:"
    )


def get_pd_text(pd_url: str) -> str:
    return (
        "📄 Также необходимо принять:\n\n"
        f"🔒 [Политика персональных данных]({pd_url})\n\n"
        "Нажмите кнопку ниже, чтобы принять:"
    )


CONFIRM_TEXT = (
    "🎉 Отлично! Зафиксировали. Продолжаем!\n\n"
    "📝 Вкратце введу в курс дела.\n\n"
    "👥 Кто мы?\n"
    "Мы команда из двух человек, которая образовалась совершенно случайно.\n"
    "Я, Андрей — организатор всего этого действия.\n"
    "Работая риелтором, снимал контент для своих объектов, и искал себе монтажёра.\n"
    "В результате я нашёл Никиту — автора курса.\n"
    "Благодаря уникальному подходу Никиты к работе, получались крутые видео, "
    "которые набирали сотни тысяч просмотров.\n"
    "И нам начало поступать много заявок на создание видео для различных объектов, "
    "а так же запросы на обучение такому монтажу.\n"
    "Мы вас услышали, и создали курс, который позволит вам делать такие же видео, "
    "или может даже более крутые видео и зарабатывать на них.\n\n"
    "🎁 Что вы получаете?\n"
    "Абсолютно БЕСПЛАТНО Вы получаете 4 урока, где узнаете основы, "
    "которые позволят сделать первые шаги и создать первые видео, а так же оценить "
    "подачу материала, и понять, подходит ли вам преподаватель.\n\n"
    "И конечно же наш платный курс, в котором вы получите все наши знания, "
    "поддержку, сопровождение и даже ПЕРВЫЕ ЗАКАЗЫ!\n\n"
    "Вам будет сразу известна вся программа курса, чтоб вы не покупали кота в мешке, "
    "а знали, что покупаете, ещё до момента покупки!\n\n"
    "✨ Итого:\n"
    "✅ Чёткое понимание, что вы покупаете, прощупав на реальных БЕСПЛАТНЫХ уроках\n"
    "✅ Концентрат знаний от людей, которые реально делают такие видео и зарабатывают на этом\n"
    "✅ Группу поддержки на весь период обучения\n"
    "✅ Личное наставничество и сопровождение\n"
    "✅ Возможность получить реальные заказы от реальных заказчиков\n\n"
    "И на выходе, вы не просто прошли обучение, а получили и отработали ценные навыки "
    "на практике, а так же знаете где найти клиентов. Дальше остаётся просто делать. "
    "Деньги не заставят себя долго ждать...\n"
    "Окупить обучение можно с первого же заказа.\n"
    "Ценник на подобные заказы колеблется в районе 30-50к руб.\n"
    "Вы даже останетесь в плюсе!\n\n"
    "🚀 Готовы начать влиять на свою жизнь, и повернуть её течение в нужную Вам сторону?\n"
    "👇 Жмите далее!"
)

GOAL_TEXT = "🎯 Какая ваша цель?"


async def get_or_create_user(session: AsyncSession, message: Message) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            funnel_stage="start"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    user = await get_or_create_user(session, message)
    offer_url, privacy_url, pd_url = await get_legal_links(session)
    if not user.consent_offer:
        text = get_greeting_text(offer_url, privacy_url)
        await message.answer(text, reply_markup=consent_offer_kb(), parse_mode="Markdown")
    elif not user.consent_personal_data:
        text = get_pd_text(pd_url)
        await message.answer(text, reply_markup=consent_pd_kb(), parse_mode="Markdown")
    else:
        user.funnel_stage = "consent_done"
        await session.commit()
        await message.answer(CONFIRM_TEXT, reply_markup=next_kb())


@router.callback_query(F.data == "accept_offer")
async def accept_offer(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.consent_offer = True
    user.funnel_stage = "offer_accepted"

    log = ConsentLog(
        user_id=user.id,
        consent_type=ConsentTypeEnum.offer,
        accepted=True
    )
    session.add(log)

    event = AnalyticsEvent(
        user_id=user.id,
        event_type="consent_offer_accepted"
    )
    session.add(event)

    await session.commit()

    # Ставим галочку на кнопке оферты
    await callback.message.edit_reply_markup(reply_markup=consent_offer_done_kb())

    # Отправляем НОВОЕ сообщение про ПДн
    _, _, pd_url = await get_legal_links(session)
    text = get_pd_text(pd_url)
    await callback.message.answer(text, reply_markup=consent_pd_kb(), parse_mode="Markdown")
    await callback.answer("✅ Оферта принята!")


@router.callback_query(F.data == "accept_pd")
async def accept_pd(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.consent_personal_data = True
    user.funnel_stage = "consent_done"

    log = ConsentLog(
        user_id=user.id,
        consent_type=ConsentTypeEnum.personal_data,
        accepted=True
    )
    session.add(log)

    event = AnalyticsEvent(
        user_id=user.id,
        event_type="consent_pd_accepted"
    )
    session.add(event)

    await session.commit()

    # Ставим галочку на кнопке ПДн
    await callback.message.edit_reply_markup(reply_markup=consent_pd_done_kb())

    # Отправляем НОВОЕ сообщение с подтверждением + главное меню
    await callback.message.answer(CONFIRM_TEXT, reply_markup=next_kb())
    await callback.answer("✅ Политика принята!")


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "next_intro")
async def next_intro(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.funnel_stage = "intro_done"
    await session.commit()

    await callback.message.answer(GOAL_TEXT, reply_markup=goal_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("goal_"))
async def goal_selected(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    goal_map = {
        "goal_own_objects": GoalEnum.own_objects,
        "goal_earn_money": GoalEnum.earn_money,
        "goal_exploring_ai": GoalEnum.exploring_ai,
    }
    user.goal = goal_map[callback.data]
    user.funnel_stage = "goal_selected"

    event = AnalyticsEvent(
        user_id=user.id,
        event_type="goal_selected",
        metadata_={"goal": callback.data}
    )
    session.add(event)
    await session.commit()

    await callback.message.answer(
        "🎬 Для более чёткого представления, что ты сможешь делать по итогам курса, "
        "вот несколько примеров реальных видео, которые мы делали:"
    )
    await callback.answer()

    videos = [
        ("files/video/видео_пример_1.mp4", "🔥 Набрал 300000 просмотров", 5),
        ("files/video/видео_пример_2.mp4", "🔥 Набрал 350000 просмотров", 20),
        ("files/video/видео_пример_3.mp4", "🔥 Набрал 325000 просмотров", 20),
    ]

    from ..services.cache import send_cached_video
    for path, caption, delay in videos:
        await asyncio.sleep(delay)
        await send_cached_video(bot, callback.from_user.id, path, caption)

    await asyncio.sleep(3)
    free_lessons_url = await get_free_lessons_link(session)
    text = (
        "🎁 Хочешь так же? Держи 4 бесплатных урока!\n\n"
        f"📚 [Бесплатные уроки]({free_lessons_url})"
    )
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=text,
        reply_markup=watched_kb(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "watched")
async def watched(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.funnel_stage = "watched_lessons"
    await session.commit()

    event = AnalyticsEvent(
        user_id=user.id,
        event_type="watched_lessons"
    )
    session.add(event)
    await session.commit()

    await callback.answer()

    from .reviews import send_reviews
    await send_reviews(callback.message, session, bot=callback.bot)
