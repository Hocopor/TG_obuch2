from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database import async_session
from shared.config import ADMIN_PASSWORD
import secrets

COOKIE_NAME = "admin_session"
SECRET_KEY = secrets.token_hex(32)

from fastapi.templating import Jinja2Templates
from pathlib import Path

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


async def get_db():
    async with async_session() as session:
        yield session


async def require_auth(request: Request):
    session_token = request.cookies.get(COOKIE_NAME)
    if not session_token or session_token != request.app.state.admin_token:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return True


async def get_current_user(request: Request):
    session_token = request.cookies.get(COOKIE_NAME)
    if not session_token or session_token != request.app.state.admin_token:
        return None
    return True
