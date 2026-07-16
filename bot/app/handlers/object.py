from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, Object, ObjectStatusEnum
from shared.funnel import advance_stage
from ..states import ObjectState
from ..keyboards import main_menu_kb, obj_cancel_kb, obj_skip_kb, obj_submit_kb

router = Router()

_SKIP_WORDS = ("нет", "-", "пропустить")


@router.callback_query(F.data == "start_object")
async def start_object(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ObjectState.waiting_name)
    await state.update_data(
        obj_name="", obj_address="", obj_description="",
        obj_photos="", obj_videos="", obj_budget=""
    )
    await callback.message.answer("🏠 Введите название объекта:", reply_markup=obj_cancel_kb())


@router.message(ObjectState.waiting_name, F.text)
async def receive_name(message: Message, state: FSMContext):
    await state.update_data(obj_name=message.text)
    await state.set_state(ObjectState.waiting_address)
    await message.answer("📍 Укажите адрес объекта:", reply_markup=obj_cancel_kb())


@router.message(ObjectState.waiting_address, F.text)
async def receive_address(message: Message, state: FSMContext):
    await state.update_data(obj_address=message.text)
    await state.set_state(ObjectState.waiting_description)
    await message.answer("📝 Что бы вы хотели видеть в ролике?", reply_markup=obj_cancel_kb())


@router.message(ObjectState.waiting_description, F.text)
async def receive_description(message: Message, state: FSMContext):
    await state.update_data(obj_description=message.text)
    await state.set_state(ObjectState.waiting_photos)
    await message.answer(
        "📷 Если есть фото — отправьте ссылки на них\n(ТОЛЬКО ССЫЛКИ, НЕ ФАЙЛЫ!!!)\n\n"
        "Или нажмите «Далее», чтобы пропустить.",
        reply_markup=obj_skip_kb()
    )


@router.message(ObjectState.waiting_photos, F.text)
async def receive_photos(message: Message, state: FSMContext):
    text = message.text
    await state.update_data(obj_photos="" if text.lower() in _SKIP_WORDS else text)
    await state.set_state(ObjectState.waiting_videos)
    await message.answer(
        "🎬 Если есть видео (особенно с дрона) — отправьте ссылки на них\n(ТОЛЬКО ССЫЛКИ, НЕ ФАЙЛЫ!!!)\n\n"
        "Или нажмите «Далее», чтобы пропустить.",
        reply_markup=obj_skip_kb()
    )


@router.callback_query(F.data == "obj_skip", ObjectState.waiting_photos)
async def skip_photos(callback: CallbackQuery, state: FSMContext):
    await state.update_data(obj_photos="")
    await state.set_state(ObjectState.waiting_videos)
    await callback.message.answer(
        "🎬 Если есть видео (особенно с дрона) — отправьте ссылки на них\n(ТОЛЬКО ССЫЛКИ, НЕ ФАЙЛЫ!!!)\n\n"
        "Или нажмите «Далее», чтобы пропустить.",
        reply_markup=obj_skip_kb()
    )
    await callback.answer()


@router.message(ObjectState.waiting_videos, F.text)
async def receive_videos(message: Message, state: FSMContext):
    text = message.text
    await state.update_data(obj_videos="" if text.lower() in _SKIP_WORDS else text)
    await state.set_state(ObjectState.waiting_budget)
    await message.answer("💰 Сколько вы готовы заплатить?", reply_markup=obj_cancel_kb())


@router.callback_query(F.data == "obj_skip", ObjectState.waiting_videos)
async def skip_videos(callback: CallbackQuery, state: FSMContext):
    await state.update_data(obj_videos="")
    await state.set_state(ObjectState.waiting_budget)
    await callback.message.answer("💰 Сколько вы готовы заплатить?", reply_markup=obj_cancel_kb())
    await callback.answer()


@router.message(ObjectState.waiting_budget, F.text)
async def receive_budget(message: Message, state: FSMContext):
    await state.update_data(obj_budget=message.text)
    data = await state.get_data()
    summary = (
        "📋 Проверьте заявку:\n\n"
        f"🏠 Название: {data.get('obj_name') or '—'}\n"
        f"📍 Адрес: {data.get('obj_address') or '—'}\n"
        f"📝 Пожелания: {data.get('obj_description') or '—'}\n"
        f"📷 Фото: {data.get('obj_photos') or '—'}\n"
        f"🎬 Видео: {data.get('obj_videos') or '—'}\n"
        f"💰 Бюджет: {data.get('obj_budget') or '—'}\n\n"
        "Отправить заявку?"
    )
    await state.set_state(ObjectState.waiting_confirm)
    await message.answer(summary, reply_markup=obj_submit_kb())


@router.callback_query(F.data == "obj_submit", ObjectState.waiting_confirm)
async def obj_submit(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    await state.clear()
    if not user:
        await callback.message.answer("⚠️ Ошибка. Начните заново.", reply_markup=main_menu_kb())
        await callback.answer()
        return
    obj = Object(
        user_id=user.id,
        object_name=data.get("obj_name") or None,
        address=data.get("obj_address") or None,
        description=data.get("obj_description") or None,
        photo_links=data.get("obj_photos") or None,
        video_links=data.get("obj_videos") or None,
        budget=data.get("obj_budget") or None,
        status=ObjectStatusEnum.accepted,
        cancelled=False,
    )
    session.add(obj)
    advance_stage(user, "object_submitted")
    await session.commit()
    await callback.message.answer("✅ Объект принят! Мы свяжемся с вами.", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "obj_cancel", StateFilter(ObjectState))
async def obj_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    entered = any(data.get(k) for k in ("obj_name", "obj_address", "obj_description", "obj_photos", "obj_videos", "obj_budget"))
    if entered:
        result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result.scalar_one_or_none()
        if user:
            obj = Object(
                user_id=user.id,
                object_name=data.get("obj_name") or None,
                address=data.get("obj_address") or None,
                description=data.get("obj_description") or None,
                photo_links=data.get("obj_photos") or None,
                video_links=data.get("obj_videos") or None,
                budget=data.get("obj_budget") or None,
                status=ObjectStatusEnum.accepted,
                cancelled=True,
            )
            session.add(obj)
            await session.commit()
    await callback.message.answer("🏠 Главное меню", reply_markup=main_menu_kb())
    await callback.answer()


@router.message(StateFilter(
    ObjectState.waiting_name, ObjectState.waiting_address, ObjectState.waiting_description,
    ObjectState.waiting_photos, ObjectState.waiting_videos, ObjectState.waiting_budget,
), ~F.text)
async def object_non_text(message: Message):
    await message.answer("⚠️ Пожалуйста, отправьте текстовое сообщение (ссылку или текст).")


@router.message(ObjectState.waiting_confirm)
async def confirm_non_button(message: Message):
    await message.answer("👇 Нажмите «✅ Отправить» или «❌ Отмена».")
