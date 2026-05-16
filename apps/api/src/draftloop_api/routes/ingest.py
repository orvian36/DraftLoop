"""POST /api/matters/:matter_id/docs — upload + register a source document."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from draftloop_api.wiring import blob_store, document_store

router = APIRouter(prefix="/api/matters/{matter_id}/docs")


@router.post("", status_code=202)
async def upload_doc(matter_id: str, file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")
    content = await file.read()
    key = f"{matter_id}/{file.filename}"
    await blob_store().put(key, content)
    store = document_store()
    await store.init_schema()
    await store.put(
        f"docs/{matter_id}/{file.filename}",
        {"status": "uploaded", "filename": file.filename, "blob_key": key},
    )
    return {"doc_id": file.filename, "status": "uploaded"}
