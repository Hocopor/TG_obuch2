import shutil
from pathlib import Path
from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from shared.models import LegalDocument, LegalDocTypeEnum
from ..dependencies import get_db, require_auth, templates

router = APIRouter(prefix="/legal", dependencies=[Depends(require_auth)])

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"


@router.get("")
async def legal_list(request: Request, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(LegalDocument).order_by(LegalDocument.uploaded_at.desc())
    )
    documents = result.scalars().all()
    return templates.TemplateResponse("legal.html", {
        "request": request,
        "documents": documents,
    })


@router.post("/upload")
async def legal_upload(
    request: Request,
    session: AsyncSession = Depends(get_db),
    document_type: str = "",
    file: UploadFile = File(...),
):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Deactivate old documents of the same type
    doc_type = LegalDocTypeEnum(document_type)
    await session.execute(
        update(LegalDocument)
        .where(LegalDocument.document_type == doc_type, LegalDocument.is_active == True)
        .values(is_active=False)
    )

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = LegalDocument(
        document_type=doc_type,
        file_path=str(file_path),
        file_name=file.filename,
        is_active=True,
    )
    session.add(doc)
    await session.commit()
    return RedirectResponse(url="/legal", status_code=303)


@router.post("/{doc_id}/activate")
async def legal_activate(
    request: Request,
    doc_id: int,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(LegalDocument).where(LegalDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return RedirectResponse(url="/legal", status_code=303)

    # Deactivate others of same type
    await session.execute(
        update(LegalDocument)
        .where(
            LegalDocument.document_type == doc.document_type,
            LegalDocument.id != doc_id,
            LegalDocument.is_active == True,
        )
        .values(is_active=False)
    )
    doc.is_active = True
    await session.commit()
    return RedirectResponse(url="/legal", status_code=303)


@router.get("/{doc_id}/download")
async def legal_download(
    doc_id: int,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(LegalDocument).where(LegalDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return RedirectResponse(url="/legal", status_code=303)
    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name,
        media_type="application/octet-stream",
    )
