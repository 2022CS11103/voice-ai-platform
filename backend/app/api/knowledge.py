from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent, Business, Document, User
from app.db.session import get_db
from app.schemas import DocumentOut, KnowledgeTextIn, WebsiteImportIn
from app.services.auth import get_current_user
from app.services.rag import ingest_text, ingest_upload, ingest_website

router = APIRouter(tags=["knowledge"])
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"


async def _owned_agent(db: AsyncSession, user: User, agent_id: int) -> Agent:
    result = await db.execute(
        select(Agent)
        .join(Business, Business.id == Agent.business_id)
        .where(Agent.id == agent_id, Business.user_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/agents/{agent_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_agent(db, user, agent_id)
    result = await db.execute(
        select(Document).where(Document.agent_id == agent_id).order_by(Document.id.desc())
    )
    return list(result.scalars().all())


@router.post("/agents/{agent_id}/documents", response_model=DocumentOut)
async def upload_document(
    agent_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_agent(db, user, agent_id)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    doc = await ingest_upload(db, agent_id, file.filename or "upload.txt", data, UPLOAD_DIR)
    return doc


@router.post("/agents/{agent_id}/knowledge", response_model=DocumentOut)
async def add_text_knowledge(
    agent_id: int,
    payload: KnowledgeTextIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_agent(db, user, agent_id)
    return await ingest_text(db, agent_id, payload.content, payload.title, source_type="text")


@router.post("/agents/{agent_id}/knowledge/website", response_model=DocumentOut)
async def import_website(
    agent_id: int,
    payload: WebsiteImportIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_agent(db, user, agent_id)
    try:
        return await ingest_website(db, agent_id, payload.url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to import website: {exc}") from exc


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document, Agent, Business)
        .join(Agent, Agent.id == Document.agent_id)
        .join(Business, Business.id == Agent.business_id)
        .where(Document.id == document_id, Business.user_id == user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    document = row[0]
    await db.delete(document)
    await db.commit()
    return {"ok": True}
