from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    User, ConsentLog, Question, Object, MailingLog, AnalyticsEvent
)
from ..keyboards import confirm_revoke_kb, main_menu_kb

router = Router()


@router.message(F.text.contains("Отозвать согласие"))
@router.callback_query(F.data == "revoke_start")
async def revoke_start(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        await event.message.answer(
            "⚠️ Вы уверены? Действие необратимо.\nВаши данные будут удалены с сервера.",
            reply_markup=confirm_revoke_kb()
        )
        await event.answer()
    else:
        await event.answer(
            "⚠️ Вы уверены? Действие необратимо.\nВаши данные будут удалены с сервера.",
            reply_markup=confirm_revoke_kb()
        )


@router.callback_query(F.data == "revoke_confirm")
async def revoke_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()

    if user:
        await session.execute(
            delete(AnalyticsEvent).where(AnalyticsEvent.user_id == user.id)
        )
        await session.execute(
            delete(MailingLog).where(MailingLog.user_id == user.id)
        )
        await session.execute(
            delete(Object).where(Object.user_id == user.id)
        )
        await session.execute(
            delete(Question).where(Question.user_id == user.id)
        )
        await session.execute(
            delete(ConsentLog).where(ConsentLog.user_id == user.id)
        )
        await session.delete(user)
        await session.commit()

    await state.clear()
    await callback.message.edit_text(
        "🗑 Ваши данные удалены.",
        reply_markup=main_menu_kb()
    )
    await callback.answer()
