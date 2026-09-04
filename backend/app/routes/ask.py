"""
NL2SQL Query Route
Endpoint for asking natural language questions against uploaded dataset DuckDB schemas.
"""

import logging
from fastapi import APIRouter, HTTPException
from app.schemas.payload import AskRequest, AskResponse
from app.routes.datasets import get_dataset_entry
from app.services.nl2sql import ask_nl2sql
from app.services.intent_router import route_intent
from app.services.hybrid_rag_service import ask_hybrid_rag
from app.services.guardrails import validate_input_guardrails, sanitize_output_guardrails
from app.services.query_processor import expand_query
from app.services.groundedness_checker import verify_groundedness
from app.core.cache_manager import global_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Ask / Intelligence Router"])

@router.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest):
    """
    Intelligent Ask Endpoint:
    Includes Input/Output Guardrails, In-Memory Caching, Query Expansion, 
    Intent Routing, and Groundedness Verification.
    """
    # 1. Input Safety Guardrail Check
    is_safe, error_msg = validate_input_guardrails(payload.question)
    if not is_safe:
        raise HTTPException(status_code=400, detail=error_msg)

    entry = get_dataset_entry(payload.dataset_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload dataset first.")

    chosen_mode = payload.mode or "auto"

    # 2. Check In-Memory Fast Cache (<5ms response time for repeat queries)
    cached_response = global_cache.get(payload.dataset_id, payload.question, chosen_mode)
    if cached_response:
        return cached_response

    # 3. Query Expansion & Acronym Normalization
    processed_question = expand_query(payload.question)

    # 4. Intent Routing
    if chosen_mode == "auto":
        target_route = route_intent(processed_question)
    else:
        target_route = chosen_mode.lower()

    try:
        if target_route == "rag":
            resp = ask_hybrid_rag(
                dataset_id=payload.dataset_id,
                question=processed_question
            )
            resp.route_used = "rag"
            
            # Groundedness Check for RAG path
            if resp.retrieved_chunks:
                evidence_text = "\n".join([c.text for c in resp.retrieved_chunks])
                is_grounded, ground_explanation = verify_groundedness(processed_question, evidence_text, resp.explanation)
                if not is_grounded:
                    resp.explanation += " (Note: Response contains synthesized interpretation based on available domain context.)"

        else:
            sample_rows = entry["metadata"].sample_rows
            resp = ask_nl2sql(
                dataset_id=payload.dataset_id,
                question=processed_question,
                sample_rows=sample_rows
            )
            resp.route_used = "nl2sql"

        # 5. Output Guardrail Sanitization
        resp.explanation = sanitize_output_guardrails(resp.explanation)

        # 6. Save in Fast Memory Cache
        global_cache.set(payload.dataset_id, payload.question, chosen_mode, resp)
        return resp

    except ValueError as val_err:
        logger.warning(f"Validation error: {val_err}")
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as err:
        logger.error(f"Error processing question '{payload.question}': {err}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query error: {str(err)}")
