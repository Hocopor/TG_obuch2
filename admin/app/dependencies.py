from datetime import timezone
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database import async_session
from shared.config import ADMIN_PASSWORD, TZ

COOKIE_NAME = "admin_session"

from fastapi.templating import Jinja2Templates
from pathlib import Path

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _msk(dt):
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ).strftime("%d.%m.%Y %H:%M")


templates.env.filters["msk"] = _msk


def _full_name(user):
    if not user:
        return "—"
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return name or "—"


_GOAL_RU = {
    "own_objects": "🏠 Свои объекты",
    "earn_money": "💰 Заработок",
    "exploring_ai": "🧠 Нейросети",
}
_STAGE_RU = {
    "start": "🟡 Начало",
    "consent_done": "✅ Согласия приняты",
    "intro_done": "📖 Интро просмотрено",
    "goal_selected": "🎯 Цель выбрана",
    "free_lessons_sent": "🎁 Уроки высланы",
    "watched_lessons": "🎓 Уроки просмотрены",
    "course_detail": "ℹ️ О курсе",
    "tariffs_viewed": "💰 Тарифы просмотрены",
    "object_submitted": "🏠 Объект предложен",
}


def _goal_ru(goal):
    if not goal:
        return "—"
    val = goal.value if hasattr(goal, "value") else goal
    return _GOAL_RU.get(val, val or "—")


def _stage_ru(stage):
    return _STAGE_RU.get(stage, stage or "—")


templates.env.globals["full_name"] = _full_name
templates.env.globals["goal_ru"] = _goal_ru
templates.env.globals["stage_ru"] = _stage_ru


async def get_db():
    async with async_session() as session:
        yield session


async def require_auth(request: Request):
    session_token = request.cookies.get(COOKIE_NAME)
    if not session_token or session_token != request.app.state.admin_token:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return True
