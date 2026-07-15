from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import LegalDocument, LegalDocTypeEnum
from shared.config import ADMINKA_URL

# Плейсхолдеры — реальные URL, пока документы не загружены
PLACEHOLDER_OFFER = "https://example.com/offer"
PLACEHOLDER_PRIVACY = "https://example.com/privacy"
PLACEHOLDER_PD = "https://example.com/personal_data"
PLACEHOLDER_FREE_LESSONS = "https://example.com/free-lessons"


async def get_active_document(session: AsyncSession, doc_type: LegalDocTypeEnum):
    result = await session.execute(
        select(LegalDocument)
        .where(
            LegalDocument.document_type == doc_type,
            LegalDocument.is_active == True,
        )
        .order_by(LegalDocument.uploaded_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_free_lessons_link(session: AsyncSession):
    doc = await get_active_document(session, LegalDocTypeEnum.free_lessons)
    if doc:
        return f"{ADMINKA_URL}/legal/{doc.id}/download"
    return PLACEHOLDER_FREE_LESSONS


async def get_legal_links(session: AsyncSession):
    offer = await get_active_document(session, LegalDocTypeEnum.offer)
    privacy = await get_active_document(session, LegalDocTypeEnum.privacy_policy)
    pd = await get_active_document(session, LegalDocTypeEnum.personal_data_policy)

    offer_url = f"{ADMINKA_URL}/legal/{offer.id}/download" if offer else PLACEHOLDER_OFFER
    privacy_url = f"{ADMINKA_URL}/legal/{privacy.id}/download" if privacy else PLACEHOLDER_PRIVACY
    pd_url = f"{ADMINKA_URL}/legal/{pd.id}/download" if pd else PLACEHOLDER_PD

    return offer_url, privacy_url, pd_url
