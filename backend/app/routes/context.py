"""
Context Document Routes
Endpoints for uploading and listing business context documents (.pdf, .txt).
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List
from app.schemas.payload import ContextUploadResponse, ContextDocSummary
from app.services.context_store import global_context_store

router = APIRouter(prefix="/api/context", tags=["Business Context"])

@router.post("/upload", response_model=ContextUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_context_document(file: UploadFile = File(...)):
    """
    Upload a business context document (.pdf, .txt, .md).
    Parses pages, chunks text, computes embeddings via BAAI/bge-small-en-v1.5, 
    and updates FAISS dense and BM25 sparse indices.
    """
    filename = file.filename or "context_doc.txt"
    file_bytes = await file.read()

    try:
        res = global_context_store.add_document(file_bytes, filename)
        return ContextUploadResponse(**res)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to process context document: {str(err)}")

@router.get("/documents", response_model=List[ContextDocSummary])
async def list_context_documents():
    """
    Lists all indexed business context documents and their chunk counts.
    """
    docs = []
    for doc_id, info in global_context_store.documents.items():
        docs.append(ContextDocSummary(
            doc_id=doc_id,
            filename=info["filename"],
            chunk_count=info["chunk_count"]
        ))
    return docs
