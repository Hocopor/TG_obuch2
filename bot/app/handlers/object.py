from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, Object
from ..states import ObjectState
from ..keyboards import object_step_kb, object_send_kb, main_menu_kb

router = Router()


@router.message(F.text == "Предложить свой объект")
@router.callback_query(F.data == "start_object")
async def start_object(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.message.answer("Введите название объекта", reply_markup=object_step_kb())
        await event.answer()
    else:
        await event.answer("Введите название объекта", reply_markup=object_step_kb())

    await state.set_state(ObjectState.waiting_name)
    await state.update_data(
        obj_name="", obj_address="", obj_description="",
        obj_photos="", obj_videos="", obj_budget=""
    )


@router.callback_query(F.data == "obj_next")
async def obj_next(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state == ObjectState.waiting_name:
        await state.set_state(ObjectState.waiting_address)
        await callback.message.edit_text("Адрес объекта", reply_markup=object_step_kb())
    elif current_state == ObjectState.waiting_address:
        await state.set_state(ObjectState.waiting_description)
        await callback.message.edit_text(
            "Что бы вы хотели видеть",
            reply_markup=object_step_kb()
        )
    elif current_state == ObjectState.waiting_description:
        await state.set_state(ObjectState.waiting_photos)
        await callback.message.edit_text(
            "Если есть фото — отправьте ссылки на них(ТОЛЬКО ССЫЛКИ, НЕ ФАЙЛЫ!!!)",
            reply_markup=object_step_kb()
        )
    elif current_state == ObjectState.waiting_photos:
        await state.set_state(ObjectState.waiting_videos)
        await callback.message.edit_text(
            "Если есть видео, особенно с дрона — отправьте ссылки на них(ТОЛЬКО ССЫЛКИ, НЕ ФАЙЛЫ!!!)",
            reply_markup=object_step_kb()
        )
    elif current_state == ObjectState.waiting_videos:
        await state.set_state(ObjectState.waiting_budget)
        await callback.message.edit_text(
            "Сколько вы готовы заплатить?",
            reply_markup=object_send_kb()
        )

    await callback.answer()


@router.callback_query(F.data == "obj_send")
async def obj_send(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    current_state = await state.get_state()
    if current_state != ObjectState.waiting_budget:
        await callback.message.answer("Заполните все поля.")
        await callback.answer()
        return

    data = await state.get_data()

    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer()
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

    await callback.message.edit_text(
        "Спасибо! Ваш объект принят. Мы свяжемся с вами.",
        reply_markup=main_menu_kb()
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "obj_cancel")
async def obj_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()

    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()

    if user and data.get("obj_name"):
        obj = Object(
            user_id=user.id,
            object_name=data.get("obj_name", ""),
            address=data.get("obj_address", ""),
            description=data.get("obj_description", ""),
            photo_links=data.get("obj_photos", ""),
            video_links=data.get("obj_videos", ""),
            budget=data.get("obj_budget", ""),
            status="pending",
            admin_notes="Пользователь отменил"
        )
        session.add(obj)
        await session.commit()

    await state.clear()
    await callback.message.edit_text("Главное меню")
    await callback.answer()


@router.message(ObjectState.waiting_name)
async def receive_name(message: Message, state: FSMContext):
    await state.update_data(obj_name=message.text)
    await message.answer("Название сохранено. Нажмите 'Далее' для продолжения.", reply_markup=object_step_kb())


@router.message(ObjectState.waiting_address)
async def receive_address(message: Message, state: FSMContext):
    await state.update_data(obj_address=message.text)
    await message.answer("Адрес сохранён. Нажмите 'Далее' для продолжения.", reply_markup=object_step_kb())


@router.message(ObjectState.waiting_description)
async def receive_description(message: Message, state: FSMContext):
    await state.update_data(obj_description=message.text)
    await message.answer("Описание сохранено. Нажмите 'Далее' для продолжения.", reply_markup=object_step_kb())


@router.message(ObjectState.waiting_photos)
async def receive_photos(message: Message, state: FSMContext):
    await state.update_data(obj_photos=message.text)
    await message.answer("Фото сохранены. Нажмите 'Далее' для продолжения.", reply_markup=object_step_kb())


@router.message(ObjectState.waiting_videos)
async def receive_videos(message: Message, state: FSMContext):
    await state.update_data(obj_videos=message.text)
    await message.answer("Видео сохранены. Нажмите 'Далее' для продолжения.", reply_markup=object_step_kb())


@router.message(ObjectState.waiting_budget)
async def receive_budget(message: Message, state: FSMContext):
    await state.update_data(obj_budget=message.text)
    await message.answer("Бюджет сохранён. Нажмите 'Отправить' для завершения.", reply_markup=object_send_kb())
