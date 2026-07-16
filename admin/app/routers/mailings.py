from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from shared.models import Mailing, MailingLog, MailingCategoryEnum, MailingStatusEnum
from datetime import datetime, timezone
from urllib.parse import urlencode
from shared.config import TZ
from ..dependencies import get_db, require_auth, templates

router = APIRouter(prefix="/mailings", dependencies=[Depends(require_auth)])

PAGE_SIZE = 50


@router.get("")
async def mailings_list(request: Request, page: int = Query(1), session: AsyncSession = Depends(get_db)):
    page = max(page, 1)
    total = (await session.execute(select(func.count(Mailing.id)))).scalar() or 0
    result = await session.execute(
        select(Mailing).order_by(Mailing.created_at.desc())
        .limit(PAGE_SIZE).offset((page - 1) * PAGE_SIZE)
    )
    mailings = result.scalars().all()
    counts = await session.execute(
        select(MailingLog.mailing_id, MailingLog.status, func.count())
        .group_by(MailingLog.mailing_id, MailingLog.status)
    )
    stats = {}
    for mid, st, c in counts.all():
        d = stats.setdefault(mid, {"sent": 0, "failed": 0})
        d[st.value] = c
    return templates.TemplateResponse("mailings.html", {
        "request": request, "mailings": mailings, "stats": stats,
        "page": page, "has_prev": page > 1, "has_next": page * PAGE_SIZE < total,
    })


@router.get("/create")
async def mailing_create_form(
    request: Request,
    message_text: str = "",
    target_category: str = "",
    scheduled_at: str = "",
):
    return templates.TemplateResponse("mailing_create.html", {
        "request": request,
        "message_text": message_text,
        "target_category": target_category,
        "scheduled_at": scheduled_at,
    })


@router.post("/create")
async def mailing_create(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    form = await request.form()
    message_text = form.get("message_text", "")
    target_category = form.get("target_category", "all")
    scheduled_at_str = form.get("scheduled_at", "")

    scheduled_at = None
    if scheduled_at_str:
        local = datetime.fromisoformat(scheduled_at_str).replace(tzinfo=TZ)
        scheduled_at = local.astimezone(timezone.utc).replace(tzinfo=None)

    status = MailingStatusEnum.pending
    if not scheduled_at:
        status = MailingStatusEnum.pending  # bot will pick it up immediately

    mailing = Mailing(
        message_text=message_text,
        target_category=MailingCategoryEnum(target_category),
        scheduled_at=scheduled_at,
        status=status,
    )
    session.add(mailing)
    await session.commit()
    return RedirectResponse(url="/mailings", status_code=303)


@router.post("/{mailing_id}/repeat")
async def mailing_repeat(
    request: Request,
    mailing_id: int,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Mailing).where(Mailing.id == mailing_id))
    mailing = result.scalar_one_or_none()
    if not mailing:
        return RedirectResponse(url="/mailings", status_code=303)
    params = urlencode({
        "message_text": mailing.message_text,
        "target_category": mailing.target_category.value,
    })
    return RedirectResponse(url=f"/mailings/create?{params}", status_code=303)


@router.post("/{mailing_id}/cancel")
async def mailing_cancel(
    request: Request,
    mailing_id: int,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Mailing).where(Mailing.id == mailing_id))
    mailing = result.scalar_one_or_none()
    if mailing and mailing.status == MailingStatusEnum.pending:
        mailing.status = MailingStatusEnum.cancelled
        await session.commit()
    return RedirectResponse(url="/mailings", status_code=303)
