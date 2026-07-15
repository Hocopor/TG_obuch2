from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from shared.models import Object, User, ObjectStatusEnum
from shared.notifier import notify_customer, notify_performer
from ..dependencies import get_db, require_auth, templates

router = APIRouter(prefix="/objects", dependencies=[Depends(require_auth)])


@router.get("")
async def objects_list(request: Request, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Object)
        .options(selectinload(Object.user))
        .order_by(Object.created_at.desc())
    )
    objects = result.scalars().all()
    return templates.TemplateResponse("objects.html", {
        "request": request,
        "objects": objects,
    })


@router.get("/{obj_id}")
async def object_detail(
    request: Request,
    obj_id: int,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Object).where(Object.id == obj_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return RedirectResponse(url="/objects", status_code=303)
    await session.refresh(obj, ["user", "assigned_user"])
    return templates.TemplateResponse("object_detail.html", {
        "request": request,
        "obj": obj,
    })


@router.post("/{obj_id}/assign")
async def object_assign(
    request: Request,
    obj_id: int,
    session: AsyncSession = Depends(get_db),
):
    form = await request.form()
    assigned_to = form.get("assigned_to", "").strip()

    result = await session.execute(select(Object).where(Object.id == obj_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return RedirectResponse(url="/objects", status_code=303)

    # Find user by telegram_id (numeric) or username (starts with @)
    user = None
    if assigned_to.isdigit():
        user_result = await session.execute(
            select(User).where(User.telegram_id == int(assigned_to))
        )
        user = user_result.scalar_one_or_none()
    elif assigned_to.startswith("@"):
        username = assigned_to[1:]
        user_result = await session.execute(
            select(User).where(User.username == username)
        )
        user = user_result.scalar_one_or_none()

    if user:
        obj.assigned_to = user.id
        obj.status = ObjectStatusEnum.assigned
        await session.commit()

        # Уведомления
        await session.refresh(obj, ["user", "assigned_user"])
        if obj.user and obj.user.telegram_id:
            await notify_customer(obj.user.telegram_id, obj.object_name)
        if user.telegram_id:
            await notify_performer(
                performer_telegram_id=user.telegram_id,
                object_name=obj.object_name,
                address=obj.address or "",
                description=obj.description or "",
                budget=obj.budget or "",
                customer_username=obj.user.username if obj.user else "",
            )

    return RedirectResponse(url=f"/objects/{obj_id}", status_code=303)


@router.post("/{obj_id}/reject")
async def object_reject(
    request: Request,
    obj_id: int,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Object).where(Object.id == obj_id))
    obj = result.scalar_one_or_none()
    if obj:
        obj.status = ObjectStatusEnum.rejected
        await session.commit()
    return RedirectResponse(url=f"/objects/{obj_id}", status_code=303)


@router.get("/{obj_id}/download")
async def object_download(
    obj_id: int,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Object).where(Object.id == obj_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return RedirectResponse(url="/objects", status_code=303)
    await session.refresh(obj, ["user", "assigned_user"])

    lines = [
        f"Объект: {obj.object_name}",
        f"Адрес: {obj.address or '—'}",
        f"Описание: {obj.description or '—'}",
        f"Фото: {obj.photo_links or '—'}",
        f"Видео: {obj.video_links or '—'}",
        f"Бюджет: {obj.budget or '—'}",
        f"Статус: {obj.status.value}",
        f"Назначен: {obj.assigned_user.first_name + ' ' + obj.assigned_user.last_name if obj.assigned_user else '—'}",
        f"Заметки: {obj.admin_notes or '—'}",
        f"Пользователь: {obj.user.first_name} {obj.user.last_name} (@{obj.user.username}) [ID: {obj.user.telegram_id}]",
        f"Дата создания: {obj.created_at.strftime('%d.%m.%Y %H:%M') if obj.created_at else '—'}",
    ]
    content = "\n".join(lines)
    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="object_{obj.id}.txt"'},
    )
