import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from shared.database import async_session
from shared.models import (
    Mailing, MailingLog, MailingStatusEnum, MailingLogStatusEnum,
    MailingCategoryEnum, User, Object, ObjectStatusEnum,
)

logger = logging.getLogger(__name__)


async def process_mailings(bot: Bot):
    async with async_session() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(Mailing).where(
                Mailing.status == MailingStatusEnum.pending,
                (
                    (Mailing.scheduled_at.is_(None))
                    | (Mailing.scheduled_at <= now)
                ),
            )
        )
        mailings = result.scalars().all()

        for mailing in mailings:
            mailing.status = MailingStatusEnum.sending
            await session.commit()

            users = await _get_target_users(session, mailing.target_category)
            sent = 0
            failed = 0

            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=mailing.message_text,
                    )
                    log = MailingLog(
                        mailing_id=mailing.id,
                        user_id=user.id,
                        status=MailingLogStatusEnum.sent,
                    )
                    session.add(log)
                    sent += 1
                except Exception as e:
                    log = MailingLog(
                        mailing_id=mailing.id,
                        user_id=user.id,
                        status=MailingLogStatusEnum.failed,
                        error_message=str(e),
                    )
                    session.add(log)
                    failed += 1
                    logger.warning("Mailing %d: failed to send to user %d: %s", mailing.id, user.id, e)

            mailing.status = MailingStatusEnum.sent
            await session.commit()
            logger.info("Mailing %d completed: sent=%d, failed=%d", mailing.id, sent, failed)


async def _get_target_users(session: AsyncSession, category: MailingCategoryEnum):
    query = select(User).where(User.consent_personal_data == True)
    if category != MailingCategoryEnum.all:
        goal_map = {
            MailingCategoryEnum.own_objects: User.goal,
            MailingCategoryEnum.earn_money: User.goal,
            MailingCategoryEnum.exploring_ai: User.goal,
        }
        goal_value_map = {
            MailingCategoryEnum.own_objects: "own_objects",
            MailingCategoryEnum.earn_money: "earn_money",
            MailingCategoryEnum.exploring_ai: "exploring_ai",
        }
        query = query.where(User.goal == goal_value_map[category])

    result = await session.execute(query)
    return result.scalars().all()


async def check_new_orders(bot: Bot):
    async with async_session() as session:
        result = await session.execute(
            select(Object).where(
                Object.status == ObjectStatusEnum.assigned,
                ~Object.admin_notes.ilike("%[notified]%"),
            )
        )
        objects = result.scalars().all()

        for obj in objects:
            if obj.assigned_to:
                user_result = await session.execute(
                    select(User).where(User.id == obj.assigned_to)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=(
                                f"Вам назначен объект «{obj.object_name}».\n"
                                f"Адрес: {obj.address or 'не указан'}\n"
                                f"Описание: {obj.description or 'не указано'}"
                            ),
                        )
                        notes = obj.admin_notes or ""
                        obj.admin_notes = f"{notes} [notified]".strip()
                        await session.commit()
                    except Exception as e:
                        logger.warning("Failed to notify user %d about object %d: %s", user.id, obj.id, e)
