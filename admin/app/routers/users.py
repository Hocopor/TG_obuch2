from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, String, func
from shared.models import User
from ..dependencies import get_db, require_auth, templates

router = APIRouter(prefix="/users", dependencies=[Depends(require_auth)])

PAGE_SIZE = 50


@router.get("")
async def users_list(
    request: Request,
    q: str = Query(None),
    page: int = Query(1),
    session: AsyncSession = Depends(get_db),
):
    conditions = []
    if q:
        term = q.strip().lstrip("@")
        pattern = f"%{term}%"
        conditions.append(or_(
            User.username.ilike(pattern),
            User.first_name.ilike(pattern),
            User.last_name.ilike(pattern),
            User.phone.ilike(pattern),
            User.telegram_id.cast(String).ilike(pattern),
        ))
    page = max(page, 1)
    total = (await session.execute(
        select(func.count(User.id)).where(*conditions)
    )).scalar() or 0
    result = await session.execute(
        select(User).where(*conditions)
        .order_by(User.created_at.desc())
        .limit(PAGE_SIZE).offset((page - 1) * PAGE_SIZE)
    )
    users = result.scalars().all()
    return templates.TemplateResponse("users.html", {
        "request": request, "users": users, "q": q,
        "page": page, "has_prev": page > 1, "has_next": page * PAGE_SIZE < total,
        "total": total,
    })


@router.get("/{telegram_id}")
async def user_detail(
    request: Request,
    telegram_id: int,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return templates.TemplateResponse("users.html", {
            "request": request,
            "users": [],
            "q": "",
            "error": "Пользователь не найден",
        })
    # Eager-load relationships
    await session.refresh(user, ["consent_logs", "questions", "objects", "events", "mailing_logs"])
    return templates.TemplateResponse("user_detail.html", {
        "request": request,
        "user": user,
    })
