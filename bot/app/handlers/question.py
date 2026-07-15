from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, Question
from shared.config import CHAT_ID
from ..keyboards import main_menu_kb

router = Router()


async def forward_to_support(message: Message, session: AsyncSession):
    """Пересылает сообщение пользователя в группу поддержки (в тему пользователя)."""
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return

    # Проверяем, принял ли пользователь обе политики
    if not user.consent_offer or not user.consent_personal_data:
        return

    # Сохраняем вопрос в БД
    question = Question(
        user_id=user.id,
        message_text=message.text or message.caption or "[медиа]",
        status="pending"
    )
    session.add(question)
    await session.commit()

    user_info = (
        f"💬 Сообщение от @{message.from_user.username or 'нет username'} "
        f"(ID: {message.from_user.id})\n\n{message.text or message.caption or ''}"
    )

    try:
        if user.support_thread_id:
            # Уже есть тема — отправляем в неё
            await message.bot.send_message(
                chat_id=CHAT_ID,
                message_thread_id=user.support_thread_id,
                text=user_info
            )
        else:
            # Создаём новую тему для пользователя
            topic_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''} (@{message.from_user.username or 'нет'})".strip()
            if len(topic_name) > 128:
                topic_name = topic_name[:125] + "..."

            topic = await message.bot.create_forum_topic(
                chat_id=CHAT_ID,
                name=topic_name
            )
            thread_id = topic.message_thread_id

            # Сохраняем thread_id пользователю
            user.support_thread_id = thread_id
            await session.commit()

            # Отправляем сообщение в новую тему
            await message.bot.send_message(
                chat_id=CHAT_ID,
                message_thread_id=thread_id,
                text=user_info
            )

        # Отправляем подтверждение пользователю
        await message.answer(
            "✅ Сообщение отправлено! Ожидайте ответа.",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        await message.answer(
            "⚠️ Не удалось отправить сообщение. Попробуйте позже.",
            reply_markup=main_menu_kb()
        )


@router.message(F.text)
async def auto_forward_text(message: Message, session: AsyncSession, state: FSMContext):
    """Автоматически пересылает текстовые сообщения в группу после принятия политик."""
    # Только личные чаты (не группы)
    if message.chat.type != "private":
        return

    # Игнорируем команды
    if message.text.startswith('/'):
        return

    # Проверяем FSM — если пользователь в состоянии (например, заполняет объект), не пересылаем
    current_state = await state.get_state()
    if current_state is not None:
        return

    await forward_to_support(message, session)


@router.message(F.photo | F.video | F.document)
async def auto_forward_media(message: Message, session: AsyncSession, state: FSMContext):
    """Автоматически пересылает медиафайлы в группу после принятия политик."""
    # Только личные чаты (не группы)
    if message.chat.type != "private":
        return

    # Проверяем FSM — если пользователь в состоянии, не пересылаем
    current_state = await state.get_state()
    if current_state is not None:
        return

    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return

    if not user.consent_offer or not user.consent_personal_data:
        return

    # Определяем тип контента
    if message.photo:
        content_type = "фото"
        file_id = message.photo[-1].file_id
        caption = message.caption or ""
    elif message.video:
        content_type = "видео"
        file_id = message.video.file_id
        caption = message.caption or ""
    else:
        content_type = "документ"
        file_id = message.document.file_id
        caption = message.caption or ""

    # Сохраняем вопрос в БД
    question = Question(
        user_id=user.id,
        message_text=f"[{content_type}] {caption}" if caption else f"[{content_type}]",
        status="pending"
    )
    session.add(question)
    await session.commit()

    user_info = (
        f"💬 {content_type.capitalize()} от @{message.from_user.username or 'нет username'} "
        f"(ID: {message.from_user.id})\n\n{caption}"
    )

    try:
        if user.support_thread_id:
            # Отправляем подпись в тему
            if caption:
                await message.bot.send_message(
                    chat_id=CHAT_ID,
                    message_thread_id=user.support_thread_id,
                    text=user_info
                )

            # Пересылаем медиафайл
            if message.photo:
                await message.bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=file_id,
                    message_thread_id=user.support_thread_id,
                    caption=caption
                )
            elif message.video:
                await message.bot.send_video(
                    chat_id=CHAT_ID,
                    video=file_id,
                    message_thread_id=user.support_thread_id,
                    caption=caption
                )
            elif message.document:
                await message.bot.send_document(
                    chat_id=CHAT_ID,
                    document=file_id,
                    message_thread_id=user.support_thread_id,
                    caption=caption
                )
        else:
            # Создаём новую тему
            topic_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''} (@{message.from_user.username or 'нет'})".strip()
            if len(topic_name) > 128:
                topic_name = topic_name[:125] + "..."

            topic = await message.bot.create_forum_topic(
                chat_id=CHAT_ID,
                name=topic_name
            )
            thread_id = topic.message_thread_id

            user.support_thread_id = thread_id
            await session.commit()

            # Отправляем медиафайл в новую тему
            if message.photo:
                await message.bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=file_id,
                    message_thread_id=thread_id,
                    caption=caption
                )
            elif message.video:
                await message.bot.send_video(
                    chat_id=CHAT_ID,
                    video=file_id,
                    message_thread_id=thread_id,
                    caption=caption
                )
            elif message.document:
                await message.bot.send_document(
                    chat_id=CHAT_ID,
                    document=file_id,
                    message_thread_id=thread_id,
                    caption=caption
                )

        await message.answer(
            "✅ Сообщение отправлено! Ожидайте ответа.",
            reply_markup=main_menu_kb()
        )
    except Exception:
        await message.answer(
            "⚠️ Не удалось отправить сообщение. Попробуйте позже.",
            reply_markup=main_menu_kb()
        )


@router.callback_query(F.data == "main_menu")
async def cancel_question(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu_kb())
    await callback.answer()
