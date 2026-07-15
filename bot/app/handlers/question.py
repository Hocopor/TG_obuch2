from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, Question
from shared.config import CHAT_ID
from ..states import QuestionState
from ..keyboards import send_question_kb, main_menu_kb

router = Router()


@router.message(F.text == "Задать вопрос")
@router.callback_query(F.data == "ask_question")
async def ask_question(event: Message | CallbackQuery, state: FSMContext, session: AsyncSession):
    if isinstance(event, CallbackQuery):
        await event.message.answer(
            "Введите свой вопрос. Ответ поступит в этот же бот.",
            reply_markup=send_question_kb()
        )
        await event.answer()
    else:
        await event.answer(
            "Введите свой вопрос. Ответ поступит в этот же бот.",
            reply_markup=send_question_kb()
        )

    await state.set_state(QuestionState.waiting_text)


@router.callback_query(F.data == "send_question")
async def send_question_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    current_state = await state.get_state()
    if current_state != QuestionState.waiting_text:
        await callback.message.answer("Сначала введите текст вопроса.")
        await callback.answer()
        return

    data = await state.get_data()
    question_text = data.get("question_text", "")
    if not question_text:
        await callback.message.answer("Вы не ввели текст вопроса. Попробуйте снова.")
        await callback.answer()
        return

    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()

    question = Question(
        user_id=user.id,
        message_text=question_text,
        status="pending"
    )
    session.add(question)
    await session.commit()

    try:
        user_info = (
            f"Вопрос от @{callback.from_user.username or 'нет username'} "
            f"(ID: {callback.from_user.id})\n\n{question_text}"
        )
        if user and user.support_thread_id:
            await callback.bot.send_message(
                chat_id=CHAT_ID,
                message_thread_id=user.support_thread_id,
                text=user_info
            )
        else:
            msg = await callback.bot.send_message(
                chat_id=CHAT_ID,
                text=user_info
            )
            if user and msg.message_thread_id:
                user.support_thread_id = msg.message_thread_id
                await session.commit()
    except Exception:
        pass

    await callback.message.edit_text(
        "Ваш вопрос отправлен! Ожидайте ответа.",
        reply_markup=main_menu_kb()
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "main_menu", QuestionState.waiting_text)
async def cancel_question(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню")
    await callback.answer()


@router.message(QuestionState.waiting_text)
async def receive_question_text(message: Message, state: FSMContext):
    await state.update_data(question_text=message.text)
    await message.answer(
        f"Ваш вопрос:\n\n{message.text}\n\nОтправить?",
        reply_markup=send_question_kb()
    )
