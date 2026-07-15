from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.models import Mailing, MailingCategoryEnum, MailingStatusEnum
from datetime import datetime
from ..dependencies import get_db, require_auth, templates

router = APIRouter(prefix="/mailings", dependencies=[Depends(require_auth)])


@router.get("")
async def mailings_list(request: Request, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Mailing).order_by(Mailing.created_at.desc()))
    mailings = result.scalars().all()
    return templates.TemplateResponse("mailings.html", {
        "request": request,
        "mailings": mailings,
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
        scheduled_at = datetime.fromisoformat(scheduled_at_str)

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
    return RedirectResponse(
        url=f"/mailings/create?message_text={mailing.message_text}&target_category={mailing.target_category.value}",
        status_code=303,
    )


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
