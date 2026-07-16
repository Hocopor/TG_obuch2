from fastapi import APIRouter, Request, Depends, BackgroundTasks, Query
from fastapi.responses import RedirectResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import timezone
from shared.models import Object, User, ObjectStatusEnum
from shared.config import TZ
from shared.notifier import notify_customer, notify_performer
from ..dependencies import get_db, require_auth, templates

router = APIRouter(prefix="/objects", dependencies=[Depends(require_auth)])

PAGE_SIZE = 50


def _full_name(u):
    if not u:
        return "—"
    n = f"{u.first_name or ''} {u.last_name or ''}".strip()
    return n or "—"


@router.get("")
async def objects_list(request: Request, page: int = Query(1), session: AsyncSession = Depends(get_db)):
    page = max(page, 1)
    total = (await session.execute(select(func.count(Object.id)))).scalar() or 0
    result = await session.execute(
        select(Object).options(selectinload(Object.user))
        .order_by(Object.created_at.desc())
        .limit(PAGE_SIZE).offset((page - 1) * PAGE_SIZE)
    )
    objects = result.scalars().all()
    return templates.TemplateResponse("objects.html", {
        "request": request, "objects": objects,
        "page": page, "has_prev": page > 1, "has_next": page * PAGE_SIZE < total,
    })


@router.get("/{obj_id}")
async def object_detail(
    request: Request,
    obj_id: int,
    error: str = Query(None),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Object).where(Object.id == obj_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return RedirectResponse(url="/objects", status_code=303)
    await session.refresh(obj, ["user", "assigned_user"])
    all_users = (await session.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    return templates.TemplateResponse("object_detail.html", {
        "request": request, "obj": obj, "all_users": all_users, "error": error,
    })


@router.post("/{obj_id}/assign")
async def object_assign(
    request: Request,
    obj_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    form = await request.form()
    assigned_to = form.get("assigned_to", "").strip()

    result = await session.execute(select(Object).where(Object.id == obj_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return RedirectResponse(url="/objects", status_code=303)

    # нельзя назначить отклонённый (сначала вернуть в «Принят»)
    if obj.status == ObjectStatusEnum.rejected:
        return RedirectResponse(url=f"/objects/{obj_id}?error=is_rejected", status_code=303)

    user = None
    val = assigned_to.lstrip("@")
    if val.isdigit():
        user = (await session.execute(select(User).where(User.telegram_id == int(val)))).scalar_one_or_none()
    if user is None and val:
        user = (await session.execute(select(User).where(User.username == val))).scalar_one_or_none()

    if not user:
        return RedirectResponse(url=f"/objects/{obj_id}?error=user_not_found", status_code=303)

    obj.assigned_to = user.id
    obj.status = ObjectStatusEnum.assigned
    await session.commit()
    await session.refresh(obj, ["user", "assigned_user"])

    object_name = obj.object_name or ""
    address = obj.address or ""
    description = obj.description or ""
    budget = obj.budget or ""
    customer_tg = obj.user.telegram_id if obj.user else None
    customer_username = obj.user.username if obj.user else ""
    performer_tg = user.telegram_id

    if customer_tg:
        background_tasks.add_task(notify_customer, customer_tg, object_name)
    if performer_tg:
        background_tasks.add_task(
            notify_performer,
            performer_telegram_id=performer_tg,
            object_name=object_name, address=address, description=description,
            budget=budget, customer_username=customer_username,
        )
    return RedirectResponse(url=f"/objects/{obj_id}", status_code=303)


@router.post("/{obj_id}/reject")
async def object_reject(request: Request, obj_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Object).where(Object.id == obj_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return RedirectResponse(url="/objects", status_code=303)
    # нельзя отклонить назначенный (сначала вернуть в «Принят»)
    if obj.status == ObjectStatusEnum.assigned:
        return RedirectResponse(url=f"/objects/{obj_id}?error=is_assigned", status_code=303)
    obj.status = ObjectStatusEnum.rejected
    await session.commit()
    return RedirectResponse(url=f"/objects/{obj_id}", status_code=303)


@router.post("/{obj_id}/reset")
async def object_reset(request: Request, obj_id: int, session: AsyncSession = Depends(get_db)):
    """Вернуть объект в статус «Принят» (снять назначение/отклонение)."""
    result = await session.execute(select(Object).where(Object.id == obj_id))
    obj = result.scalar_one_or_none()
    if obj:
        obj.status = ObjectStatusEnum.accepted
        obj.assigned_to = None
        await session.commit()
    return RedirectResponse(url=f"/objects/{obj_id}", status_code=303)


@router.get("/{obj_id}/download")
async def object_download(obj_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Object).where(Object.id == obj_id))
    obj = result.scalar_one_or_none()
    if not obj:
        return RedirectResponse(url="/objects", status_code=303)
    await session.refresh(obj, ["user", "assigned_user"])
    created = (
        obj.created_at.replace(tzinfo=timezone.utc).astimezone(TZ).strftime("%d.%m.%Y %H:%M")
        if obj.created_at else "—"
    )
    lines = [
        f"Объект: {obj.object_name or '—'}",
        f"Отменён пользователем: {'ДА' if obj.cancelled else 'нет'}",
        f"Адрес: {obj.address or '—'}",
        f"Описание: {obj.description or '—'}",
        f"Фото: {obj.photo_links or '—'}",
        f"Видео: {obj.video_links or '—'}",
        f"Бюджет: {obj.budget or '—'}",
        f"Статус: {obj.status.value}",
        f"Назначен: {_full_name(obj.assigned_user)}",
        f"Заметки: {obj.admin_notes or '—'}",
        f"Пользователь: {_full_name(obj.user)} (@{obj.user.username if obj.user else '—'}) [ID: {obj.user.telegram_id if obj.user else '—'}]",
        f"Дата создания: {created}",
    ]
    return PlainTextResponse(
        "\n".join(lines),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="object_{obj.id}.txt"'},
    )
