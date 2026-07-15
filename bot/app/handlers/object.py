from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, Object
from ..states import ObjectState
from ..keyboards import main_menu_kb

router = Router()


@router.callback_query(F.data == "start_object")
async def start_object(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🏠 Введите название объекта:")
    await callback.answer()
    await state.set_state(ObjectState.waiting_name)
    await state.update_data(
        obj_name="", obj_address="", obj_description="",
        obj_photos="", obj_videos="", obj_budget=""
    )


@router.message(ObjectState.waiting_name)
async def receive_name(message: Message, state: FSMContext):
    await state.update_data(obj_name=message.text)
    await state.set_state(ObjectState.waiting_address)
    await message.answer("📍 Укажите адрес объекта:")


@router.message(ObjectState.waiting_address)
async def receive_address(message: Message, state: FSMContext):
    await state.update_data(obj_address=message.text)
    await state.set_state(ObjectState.waiting_description)
    await message.answer(
        "📝 Опишите, что бы вы хотели видеть в ролике:"
    )


@router.message(ObjectState.waiting_description)
async def receive_description(message: Message, state: FSMContext):
    await state.update_data(obj_description=message.text)
    await state.set_state(ObjectState.waiting_photos)
    await message.answer(
        "📷 Если есть фото — отправьте ссылки на них\n(ТОЛЬКО ССЫЛКИ, НЕ ФАЙЛЫ!!!)\n\n"
        "Или напишите «нет», чтобы пропустить."
    )


@router.message(ObjectState.waiting_photos)
async def receive_photos(message: Message, state: FSMContext):
    text = message.text
    if text and text.lower() not in ("нет", "нет", "-", "пропустить"):
        await state.update_data(obj_photos=text)
    else:
        await state.update_data(obj_photos="")
    await state.set_state(ObjectState.waiting_videos)
    await message.answer(
        "🎬 Если есть видео (особенно с дрона) — отправьте ссылки на них\n(ТОЛЬКО ССЫЛКИ, НЕ ФАЙЛЫ!!!)\n\n"
        "Или напишите «нет», чтобы пропустить."
    )


@router.message(ObjectState.waiting_videos)
async def receive_videos(message: Message, state: FSMContext):
    text = message.text
    if text and text.lower() not in ("нет", "нет", "-", "пропустить"):
        await state.update_data(obj_videos=text)
    else:
        await state.update_data(obj_videos="")
    await state.set_state(ObjectState.waiting_budget)
    await message.answer("💰 Сколько вы готовы заплатить?")


@router.message(ObjectState.waiting_budget)
async def receive_budget(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(obj_budget=message.text)

    data = await state.get_data()

    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("⚠️ Ошибка. Начните заново.", reply_markup=main_menu_kb())
        await state.clear()
        return

    obj = Object(
        user_id=user.id,
        object_name=data.get("obj_name", ""),
        address=data.get("obj_address", ""),
        description=data.get("obj_description", ""),
        photo_links=data.get("obj_photos", ""),
        video_links=data.get("obj_videos", ""),
        budget=data.get("obj_budget", ""),
        status="pending"
    )
    session.add(obj)

    user.funnel_stage = "object_submitted"
    await session.commit()

    await message.answer(
        "✅ Объект принят! Мы свяжемся с вами.",
        reply_markup=main_menu_kb()
    )
    await state.clear()


@router.callback_query(F.data == "obj_cancel")
async def obj_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu_kb())
    await callback.answer()
