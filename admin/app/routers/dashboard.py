from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from shared.models import User, Object, Mailing, Question, GoalEnum
from ..dependencies import get_db, require_auth, templates

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/")
async def dashboard(request: Request, session: AsyncSession = Depends(get_db)):
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    total_objects = (await session.execute(select(func.count(Object.id)))).scalar() or 0
    pending_objects = (await session.execute(
        select(func.count(Object.id)).where(Object.status == "pending")
    )).scalar() or 0
    total_mailings = (await session.execute(select(func.count(Mailing.id)))).scalar() or 0
    total_questions = (await session.execute(select(func.count(Question.id)))).scalar() or 0

    consent_done = (await session.execute(
        select(func.count(User.id)).where(User.consent_offer == True, User.consent_personal_data == True)
    )).scalar() or 0
    goal_selected = (await session.execute(
        select(func.count(User.id)).where(User.goal.isnot(None))
    )).scalar() or 0

    own_objects = (await session.execute(
        select(func.count(User.id)).where(User.goal == GoalEnum.own_objects)
    )).scalar() or 0
    earn_money = (await session.execute(
        select(func.count(User.id)).where(User.goal == GoalEnum.earn_money)
    )).scalar() or 0
    exploring_ai = (await session.execute(
        select(func.count(User.id)).where(User.goal == GoalEnum.exploring_ai)
    )).scalar() or 0

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_users": total_users,
        "total_objects": total_objects,
        "pending_objects": pending_objects,
        "total_mailings": total_mailings,
        "total_questions": total_questions,
        "consent_done": consent_done,
        "goal_selected": goal_selected,
        "own_objects": own_objects,
        "earn_money": earn_money,
        "exploring_ai": exploring_ai,
    })
