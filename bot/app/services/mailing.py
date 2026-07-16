import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter

from shared.database import async_session
from shared.models import (
    Mailing, MailingLog, MailingStatusEnum, MailingLogStatusEnum,
    MailingCategoryEnum, User,
)

logger = logging.getLogger(__name__)


async def process_mailings(bot: Bot):
    # 1) выбрать готовые рассылки, пометить sending, собрать получателей — под короткой сессией
    async with async_session() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(Mailing).where(
                Mailing.status == MailingStatusEnum.pending,
                (Mailing.scheduled_at.is_(None)) | (Mailing.scheduled_at <= now),
            )
        )
        mailings = result.scalars().all()
        jobs = []
        for mailing in mailings:
            mailing.status = MailingStatusEnum.sending
            recipients = await _get_target_users(session, mailing.target_category)
            jobs.append((mailing.id, mailing.message_text, [(u.id, u.telegram_id) for u in recipients]))
        await session.commit()

    # 2) отправка — без удержания сессии
    for mailing_id, text, recipients in jobs:
        results = []  # (user_id, MailingLogStatusEnum, error|None)
        sent = failed = 0
        for user_id, tg_id in recipients:
            ok, err = await _send_one(bot, tg_id, text)
            if ok:
                results.append((user_id, MailingLogStatusEnum.sent, None))
                sent += 1
            else:
                results.append((user_id, MailingLogStatusEnum.failed, err))
                failed += 1
            await asyncio.sleep(0.05)

        # 3) записать логи батчем и финальный статус
        async with async_session() as session:
            for user_id, st, err in results:
                session.add(MailingLog(
                    mailing_id=mailing_id, user_id=user_id, status=st, error_message=err,
                ))
            mailing = await session.get(Mailing, mailing_id)
            if mailing:
                mailing.status = (
                    MailingStatusEnum.error if (sent == 0 and failed > 0)
                    else MailingStatusEnum.sent
                )
            await session.commit()
        logger.info("Mailing %d completed: sent=%d, failed=%d", mailing_id, sent, failed)


async def _send_one(bot: Bot, tg_id: int, text: str):
    """Отправка одному с одним повтором при RetryAfter. Возвращает (ok, error_str|None)."""
    try:
        await bot.send_message(chat_id=tg_id, text=text)
        return True, None
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        try:
            await bot.send_message(chat_id=tg_id, text=text)
            return True, None
        except Exception as e2:
            return False, str(e2)
    except Exception as e:
        return False, str(e)


async def _get_target_users(session: AsyncSession, category: MailingCategoryEnum):
    query = select(User).where(User.consent_personal_data == True)
    if category != MailingCategoryEnum.all:
        goal_value_map = {
            MailingCategoryEnum.own_objects: "own_objects",
            MailingCategoryEnum.earn_money: "earn_money",
            MailingCategoryEnum.exploring_ai: "exploring_ai",
        }
        query = query.where(User.goal == goal_value_map[category])
    result = await session.execute(query)
    return result.scalars().all()
