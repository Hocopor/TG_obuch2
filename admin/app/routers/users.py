from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from shared.models import User
from ..dependencies import get_db, require_auth, templates

router = APIRouter(prefix="/users", dependencies=[Depends(require_auth)])


@router.get("")
async def users_list(
    request: Request,
    q: str = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
                User.telegram_id.cast(str).ilike(pattern),
            )
        )
    result = await session.execute(stmt)
    users = result.scalars().all()
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users,
        "q": q,
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
