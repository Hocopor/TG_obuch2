from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, Question
from ..states import QuestionState
from ..keyboards import question_kb, home_kb
from ..services.support_service import deliver_to_support, deliver_text_to_support

router = Router()


@router.callback_query(F.data == "ask_question")
async def ask_question(callback: CallbackQuery, state: FSMContext):
    await state.set_state(QuestionState.waiting_text)
    await state.update_data(q_text="")
    await callback.message.answer(
        "✍️ Введите свой вопрос. Ответ поступит в этот же бот.",
        reply_markup=question_kb()
    )
    await callback.answer()


@router.message(QuestionState.waiting_text, F.text)
async def receive_question_text(message: Message, state: FSMContext):
    await state.update_data(q_text=message.text)
    await state.set_state(QuestionState.confirm)
    await message.answer(
        f"📝 Ваш вопрос:\n\n{message.text}\n\nОтправить?",
        reply_markup=question_kb()
    )


@router.message(QuestionState.waiting_text)
async def question_non_text(message: Message):
    await message.answer("⚠️ Пожалуйста, введите текст вопроса.")


@router.callback_query(F.data == "question_send")
async def question_send(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    text = (data.get("q_text") or "").strip()
    if not text:
        await callback.answer("Сначала введите текст вопроса", show_alert=True)
        return

    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    if not user or not user.consent_offer or not user.consent_personal_data:
        await state.clear()
        await callback.message.answer("⚠️ Ошибка. Начните с /start")
        await callback.answer()
        return

    session.add(Question(user_id=user.id, message_text=text, status="pending"))
    await session.commit()

    ok = await deliver_text_to_support(bot, session, user, f"💬 Вопрос:\n\n{text}")
    await state.clear()
    if ok:
        await callback.message.answer("✅ Вопрос отправлен! Ожидайте ответа.", reply_markup=home_kb())
    else:
        await callback.message.answer("⚠️ Не удалось отправить. Попробуйте позже.", reply_markup=home_kb())
    await callback.answer()


# ── Единая автопересылка: любое сообщение вне состояний (кроме команд) уходит в поддержку ──
@router.message(StateFilter(None), F.chat.type == "private")
async def auto_forward(message: Message, session: AsyncSession, bot: Bot):
    if message.text and message.text.startswith("/"):
        return  # команды обрабатывает unknown_command в start.py

    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if not user or not user.consent_offer or not user.consent_personal_data:
        return

    session.add(Question(
        user_id=user.id,
        message_text=message.text or message.caption or "[медиа]",
        status="pending",
    ))
    await session.commit()

    ok = await deliver_to_support(bot, session, user, message)
    if not ok:
        await message.answer("⚠️ Не удалось отправить сообщение. Попробуйте позже.")
