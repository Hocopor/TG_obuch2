import os
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from shared.models import LegalDocument, LegalDocTypeEnum
from ..dependencies import get_db, require_auth, templates

router = APIRouter(prefix="/legal")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
ALLOWED_EXT = {".pdf", ".doc", ".docx", ".txt"}
MAX_SIZE = 20 * 1024 * 1024  # 20 МБ
MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain; charset=utf-8",
}


@router.get("")
async def legal_list(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _auth: bool = Depends(require_auth),
):
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
    document_type: str = Form(...),
    file: UploadFile = File(...),
    _auth: bool = Depends(require_auth),
):
    try:
        doc_type = LegalDocTypeEnum(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неизвестный тип документа")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail="Недопустимый тип файла. Разрешены: pdf, doc, docx, txt",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    disk_name = uuid4().hex + ext
    file_path = UPLOAD_DIR / disk_name

    size = 0
    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_SIZE:
                f.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="Файл больше 20 МБ")
            f.write(chunk)

    # Деактивировать прежние документы этого типа
    await session.execute(
        update(LegalDocument)
        .where(LegalDocument.document_type == doc_type, LegalDocument.is_active == True)
        .values(is_active=False)
    )

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
    _auth: bool = Depends(require_auth),
):
    result = await session.execute(
        select(LegalDocument).where(LegalDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return RedirectResponse(url="/legal", status_code=303)

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
    ext = Path(doc.file_path).suffix.lower()
    media_type = MEDIA_TYPES.get(ext, "application/octet-stream")
    disposition = "inline" if ext == ".pdf" else "attachment"
    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name,
        media_type=media_type,
        content_disposition_type=disposition,
    )
