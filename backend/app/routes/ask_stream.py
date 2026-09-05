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
    mode: str = "auto"

@router.post("/stream")
async def ask_stream(req: StreamQueryRequest):
    """
    Streams LLM response word-by-word using Server-Sent Events (SSE)
    along with real-time status updates (Routing -> Querying/Retrieving -> Synthesizing).
    """
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

    async def generate_events():
        try:
            # Step 1: Send Intent Routing Status
            yield f"data: {json.dumps({'type': 'status', 'text': '🔍 Analyzing query intent & selecting engine...'})}\n\n"
            await asyncio.sleep(0.1)

            mode = req.mode
            if mode == 'auto':
                intent = route_intent(question, dataset_id=req.dataset_id)
            elif mode == 'rag':
                intent = 'rag'
            else:
                intent = 'nl2sql'

            if intent in ["nl2sql", "SQL"]:
                yield f"data: {json.dumps({'type': 'status', 'text': '⚡ Executing DuckDB SQL Query & summarizing stats...'})}\n\n"
                await asyncio.sleep(0.1)

                sql_res = ask_nl2sql(req.dataset_id, question)
                answer_text = sql_res.explanation

                meta_event = {
                    'type': 'meta',
                    'route_used': 'nl2sql',
                    'engine': 'DuckDB SQL Engine',
                    'sql': sql_res.sql,
                    'results': sql_res.results,
                    'row_count': sql_res.row_count,
                    'question': question
                }
                yield f"data: {json.dumps(meta_event)}\n\n"

            else:
                yield f"data: {json.dumps({'type': 'status', 'text': '📚 Searching Business Knowledge Base (FAISS + BM25)...'})}\n\n"
                await asyncio.sleep(0.1)

                rag_res = ask_hybrid_rag(req.dataset_id, question)
                answer_text = rag_res.explanation
                chunks_dict = [c.model_dump() for c in rag_res.retrieved_chunks] if hasattr(rag_res, 'retrieved_chunks') and rag_res.retrieved_chunks else []

                meta_event = {
                    'type': 'meta',
                    'route_used': 'rag',
                    'engine': 'Business Knowledge Base (Hybrid RAG)',
                    'retrieved_chunks': chunks_dict,
                    'question': question
                }
                yield f"data: {json.dumps(meta_event)}\n\n"

            # Step 3: Stream Words
            yield f"data: {json.dumps({'type': 'status', 'text': '🤖 Synthesizing AI executive insights...'})}\n\n"

            words = answer_text.split(" ")
            for i, word in enumerate(words):
                suffix = " " if i < len(words) - 1 else ""
                yield f"data: {json.dumps({'type': 'content', 'delta': word + suffix})}\n\n"
                await asyncio.sleep(0.015)

        except Exception as err:
            err_msg = f"⚠️ Notice: Unable to complete query processing. ({str(err)})"
            yield f"data: {json.dumps({'type': 'error', 'text': err_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'content', 'delta': err_msg})}\n\n"

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(generate_events(), media_type="text/event-stream")
