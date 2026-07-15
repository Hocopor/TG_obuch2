from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.models import Settings
from ..dependencies import get_db, require_auth, templates

router = APIRouter(prefix="/settings")


@router.get("")
async def settings_page(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _auth: bool = Depends(require_auth),
):
    result = await session.execute(select(Settings))
    settings_list = result.scalars().all()
    settings = {s.key: s.value or "" for s in settings_list}
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": settings,
    })


@router.post("")
async def settings_save(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _auth: bool = Depends(require_auth),
    proxy_url: str = Form(""),
):
    for key, value in [("proxy_url", proxy_url)]:
        result = await session.execute(
            select(Settings).where(Settings.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = Settings(key=key, value=value)
            session.add(setting)
    await session.commit()
    return RedirectResponse(url="/settings", status_code=303)
