import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, ConsentLog, ConsentTypeEnum, GoalEnum, AnalyticsEvent
from shared.config import ADMINKA_URL
from shared.funnel import advance_stage
from shared.database import async_session
from ..keyboards import consent_kb, consent_done_kb, next_kb, goal_kb, watched_kb, main_menu_kb
from ..services.legal import get_legal_links, get_free_lessons_link
from ..services.delayed import run_detached

router = Router()

WELCOME_TEXT = (
    "🎬 Хочешь научиться создавать крутые видео для объектов недвижимости "
    "с помощью ИИ, которые набирают миллионы просмотров?\n\n"
    "📚 Внутри бесплатные уроки, кейсы, и возможность записаться на обучение!\n\n"
    "👇 Используй возможность, жми /start"
)


def get_consent_text(offer_url: str, privacy_url: str, pd_url: str) -> str:
    return (
        "👋 Приветствуем в нашем боте!\n\n"
        "Согласно требований законодательства РФ, для продолжения необходимо "
        "ознакомиться и принять:\n\n"
        f"📄 [Оферта]({offer_url})\n"
        f"🔒 [Политика конфиденциальности]({privacy_url})\n"
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
    "✅ Концентрат знаний от людей, которые не просто сделали видео, ради показухи, "
    "для обучения, а от людей, которые в реальности делают такие видео и зарабатывают на этом\n"
    "✅ Группу поддержки на весь период обучения\n"
    "✅ Личное наставничество и сопровождение\n"
    "✅ Возможность получить реальные заказы, от реальных заказчиков (мы предоставим вам заказы)\n\n"
    "И на выходе, вы не просто прошли обучение, а получили и отработали ценные навыки "
    "на практике, а так же знаете где найти клиентов. Дальше остаётся просто делать. "
    "Деньги не заставят себя долго ждать...\n"
    "Окупить обучение можно с первого же заказа.\n"
    "Ценник на подобные заказы колеблется в районе 30-50к руб.\n"
    "Вы даже останетесь в плюсе!\n\n"
    "🚀 Готовы начать влиять на свою жизнь, и повернуть её течение в нужную Вам сторону?\n"
    "👇 Жмите далее!"
)

GOAL_TEXT = "🎯 Какая у вас цель?"

GOAL_RESPONSES = {
    "goal_own_objects": (
        "🏡 Хорошие ролики сегодня продают не только объект, но и самого агента.\n\n"
        "Большинство риэлторов до сих пор выкладывают обычные фото. Пока конкуренты "
        "только начинают разбираться в ИИ, вы можете уже сейчас делать презентации, "
        "которые цепляют внимание клиентов.\n\n"
        "Один качественный ролик способен окупить обучение многократно."
    ),
    "goal_earn_money": (
        "📦 За последний месяц к нам поступило более 150 запросов на создание роликов.\n\n"
        "Часть заказов мы были вынуждены отказаться — физически не успеваем.\n\n"
        "Такие проекты могли бы выполнять наши ученики.\n\n"
        "Сейчас спрос значительно выше предложения.\n\n"
        "🚀 Поэтому именно сейчас проще всего зайти в эту нишу."
    ),
    "goal_exploring_ai": (
        "🧠 Отличное решение.\n\n"
        "Сейчас ИИ становится обычным рабочим инструментом практически в любой профессии.\n\n"
        "На этом обучении вы получите практический навык, который сможете применять "
        "не только в недвижимости, но и в других проектах."
    ),
}


async def get_or_create_user(session: AsyncSession, message: Message) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        changed = False
        if user.username != message.from_user.username:
            user.username = message.from_user.username
            changed = True
        if user.first_name != message.from_user.first_name:
            user.first_name = message.from_user.first_name
            changed = True
        if user.last_name != message.from_user.last_name:
            user.last_name = message.from_user.last_name
            changed = True
        if changed:
            await session.commit()
        return user

    user = User(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        funnel_stage="start",
    )
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one()
    return user


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message)
    if user.consent_offer and user.consent_personal_data:
        await message.answer("🏠 Главное меню", reply_markup=main_menu_kb())
        return
    offer_url, privacy_url, pd_url = await get_legal_links(session)
    await message.answer(
        get_consent_text(offer_url, privacy_url, pd_url),
        reply_markup=consent_kb(),
        parse_mode="Markdown",
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Главное меню", reply_markup=main_menu_kb())


@router.callback_query(F.data == "accept_all")
async def accept_all(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.consent_offer = True
    user.consent_personal_data = True
    advance_stage(user, "consent_done")

    session.add(ConsentLog(user_id=user.id, consent_type=ConsentTypeEnum.offer, accepted=True))
    session.add(ConsentLog(user_id=user.id, consent_type=ConsentTypeEnum.personal_data, accepted=True))
    session.add(AnalyticsEvent(user_id=user.id, event_type="consent_accepted"))
    await session.commit()

    try:
        await callback.message.edit_reply_markup(reply_markup=consent_done_kb())
    except Exception:
        pass
    await callback.message.answer(CONFIRM_TEXT, reply_markup=next_kb())
    await callback.answer("✅ Принято!")


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

    advance_stage(user, "intro_done")
    await session.commit()

    await callback.message.answer(GOAL_TEXT, reply_markup=goal_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("goal_"))
async def goal_selected(callback: CallbackQuery, session: AsyncSession, bot: Bot, scheduler):
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
    advance_stage(user, "goal_selected")
    session.add(AnalyticsEvent(user_id=user.id, event_type="goal_selected", metadata_={"goal": callback.data}))
    await session.commit()

    free_lessons_url = await get_free_lessons_link(session)
    tg_id = callback.from_user.id

    await callback.answer()
    await bot.send_message(tg_id, GOAL_RESPONSES[callback.data])
    await bot.send_message(
        tg_id,
        "🎬 Для более чёткого представления, что ты сможешь делать по итогам курса, "
        "вот несколько примеров реальных видео, которые мы делали:"
    )
    run_detached(send_funnel_examples(bot, tg_id, free_lessons_url, scheduler))


async def send_funnel_examples(bot: Bot, tg_id: int, free_lessons_url: str, scheduler):
    from ..services.cache import send_cached_video
    from .reviews import send_funnel_reviews

    videos = [
        ("files/video/видео_пример_1.mp4", "🔥 Набрал 300000 просмотров", 5),
        ("files/video/видео_пример_2.mp4", "🔥 Набрал 350000 просмотров", 20),
        ("files/video/видео_пример_3.mp4", "🔥 Набрал 325000 просмотров", 20),
    ]
    for path, caption, delay in videos:
        await asyncio.sleep(delay)
        await send_cached_video(bot, tg_id, path, caption)

    await asyncio.sleep(30)
    text = (
        "🎁 Хочешь так же? Держи 4 бесплатных урока!\n\n"
        f"📚 [Бесплатные уроки]({free_lessons_url})"
    )
    await bot.send_message(tg_id, text, reply_markup=watched_kb(), parse_mode="Markdown")

    # запланировать отзывы через 30 минут (или раньше — по кнопке «Посмотрел»)
    try:
        scheduler.add_job(
            send_funnel_reviews,
            trigger="date",
            run_date=datetime.now() + timedelta(minutes=30),
            args=[bot, tg_id],
            id=f"reviews_{tg_id}",
            replace_existing=True,
        )
    except Exception:
        pass

    async with async_session() as s:
        u = (await s.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
        if u:
            advance_stage(u, "free_lessons_sent")
            await s.commit()


@router.callback_query(F.data == "watched")
async def watched(callback: CallbackQuery, bot: Bot, scheduler):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    tg_id = callback.from_user.id
    try:
        scheduler.remove_job(f"reviews_{tg_id}")
    except Exception:
        pass
    from .reviews import send_funnel_reviews
    run_detached(send_funnel_reviews(bot, tg_id))


@router.message(F.text.startswith("/"), StateFilter(None), F.chat.type == "private")
async def unknown_command(message: Message):
    await message.answer("🤷 Не знаю такой команды. /menu — главное меню.")
