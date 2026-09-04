import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.intent_router import route_intent
from app.services.guardrails import validate_input_guardrails
from app.services.nl2sql import ask_nl2sql
from app.services.hybrid_rag_service import ask_hybrid_rag
from app.core.redis_cache import system_cache

router = APIRouter(prefix="/api/ask", tags=["Streaming Chat"])

class StreamQueryRequest(BaseModel):
    dataset_id: str = "default"
    question: str

@router.post("/stream")
async def ask_stream(req: StreamQueryRequest):
    """Streams LLM response using Server-Sent Events (SSE)."""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Guardrail input check
    is_safe, error_msg = validate_input_guardrails(question)
    if not is_safe:
        async def safe_error_stream():
            yield f"data: {json.dumps({'type': 'content', 'delta': error_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
        return StreamingResponse(safe_error_stream(), media_type="text/event-stream")

    # Cache check
    cache_key = f"stream:{req.dataset_id}:{question}"
    cached_res = system_cache.get(cache_key)
    if cached_res:
        async def cached_stream():
            yield f"data: {json.dumps({'type': 'meta', 'engine': cached_res.get('engine'), 'citations': cached_res.get('citations')})}\n\n"
            for word in cached_res["answer"].split(" "):
                yield f"data: {json.dumps({'type': 'content', 'delta': word + ' '})}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    async def generate_events():
        # Route intent
        intent = route_intent(question)
        
        if intent == "SQL":
            sql_res = ask_nl2sql(req.dataset_id, question)
            answer_text = sql_res.explanation
            citations = [{"doc": "DuckDB SQL Query", "page": 1}]
            
            yield f"data: {json.dumps({'type': 'meta', 'engine': 'DuckDB SQL Engine', 'citations': citations})}\n\n"
            
            words = answer_text.split(" ")
            for i, word in enumerate(words):
                suffix = " " if i < len(words) - 1 else ""
                yield f"data: {json.dumps({'type': 'content', 'delta': word + suffix})}\n\n"
                await asyncio.sleep(0.015)
                
            system_cache.set(cache_key, {"answer": answer_text, "engine": "DuckDB SQL Engine", "citations": citations})
        else:
            rag_res = ask_hybrid_rag(req.dataset_id, question)
            answer_text = rag_res.explanation
            citations = [{"doc": c.source_doc, "page": c.page_number} for c in rag_res.retrieved_chunks]
            
            yield f"data: {json.dumps({'type': 'meta', 'engine': 'Business Knowledge Base (Hybrid RAG)', 'citations': citations})}\n\n"
            
            words = answer_text.split(" ")
            for i, word in enumerate(words):
                suffix = " " if i < len(words) - 1 else ""
                yield f"data: {json.dumps({'type': 'content', 'delta': word + suffix})}\n\n"
                await asyncio.sleep(0.015)
                
            system_cache.set(cache_key, {"answer": answer_text, "engine": "Business Knowledge Base (Hybrid RAG)", "citations": citations})

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(generate_events(), media_type="text/event-stream")
