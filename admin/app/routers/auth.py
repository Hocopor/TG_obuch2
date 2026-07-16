import asyncio
import secrets
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from shared.config import ADMIN_PASSWORD

router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    from ..dependencies import templates
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    if secrets.compare_digest(password, ADMIN_PASSWORD):
        token = secrets.token_hex(32)
        request.app.state.admin_token = token
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("admin_session", token, httponly=True, samesite="lax")
        return response
    await asyncio.sleep(1)
    from ..dependencies import templates
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный пароль"})


@router.get("/logout")
async def logout(request: Request):
    request.app.state.admin_token = None
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("admin_session")
    return response
