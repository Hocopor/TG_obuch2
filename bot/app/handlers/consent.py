from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    User, ConsentLog, ConsentTypeEnum, Question, Object, MailingLog,
    AnalyticsEvent, ObjectStatusEnum,
)
from shared.config import CHAT_ID
from ..keyboards import confirm_revoke_kb, consent_kb
from ..services.legal import get_legal_links
from .start import get_consent_text

router = Router()


@router.callback_query(F.data == "revoke_start")
async def revoke_start(callback: CallbackQuery):
    await callback.message.answer(
        "⚠️ Вы уверены? Действие необратимо.\nВаши данные будут удалены с сервера.",
        reply_markup=confirm_revoke_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "revoke_confirm")
async def revoke_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()

    if user:
        tid = user.telegram_id
        thread_id = user.support_thread_id

        # 1) Снять назначения чужих объектов на этого пользователя (иначе FK-ошибка при удалении)
        await session.execute(
            update(Object)
            .where(Object.assigned_to == user.id)
            .values(assigned_to=None, status=ObjectStatusEnum.accepted)
        )

        # 2) Журнал согласий храним обезличенным (152-ФЗ):
        #    новые записи об отзыве + обезличивание старых записей этого пользователя
        session.add(ConsentLog(user_id=None, telegram_id=tid, consent_type=ConsentTypeEnum.offer, accepted=False))
        session.add(ConsentLog(user_id=None, telegram_id=tid, consent_type=ConsentTypeEnum.personal_data, accepted=False))
        await session.execute(
            update(ConsentLog)
            .where(ConsentLog.user_id == user.id)
            .values(telegram_id=tid, user_id=None)
        )

        # 3) Удаляем остальные данные и самого пользователя
        await session.execute(delete(AnalyticsEvent).where(AnalyticsEvent.user_id == user.id))
        await session.execute(delete(MailingLog).where(MailingLog.user_id == user.id))
        await session.execute(delete(Object).where(Object.user_id == user.id))
        await session.execute(delete(Question).where(Question.user_id == user.id))
        await session.delete(user)
        await session.commit()

        # 4) Пытаемся удалить тему поддержки (персональные данные в группе)
        if thread_id:
            try:
                await bot.delete_forum_topic(CHAT_ID, thread_id)
            except Exception:
                pass

    await state.clear()

    try:
        await callback.message.edit_text("🗑 Ваши данные удалены.")
    except Exception:
        await callback.message.answer("🗑 Ваши данные удалены.")

    offer_url, privacy_url, pd_url = await get_legal_links(session)
    await callback.message.answer(
        get_consent_text(offer_url, privacy_url, pd_url),
        reply_markup=consent_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()
