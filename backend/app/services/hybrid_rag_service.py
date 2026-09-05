"""
Hybrid RAG Service
Grounded answer generation using retrieved context chunks and Groq LLM with inline citations.
"""

from typing import List
from groq import Groq
from app.core.config import settings
from app.schemas.payload import AskResponse, RetrievedChunk
from app.services.context_store import global_context_store

def ask_hybrid_rag(dataset_id: str, question: str) -> AskResponse:
    """
    Executes Hybrid RAG pipeline:
    1. Hybrid retrieval (FAISS dense + BM25 sparse + RRF + Cross-Encoder reranking)
    2. Grounded LLM prompt construction with chunk inline citation rules
    3. LLM generation of plain-language cited explanation
    """
    retrieved_chunks: List[RetrievedChunk] = global_context_store.hybrid_search(question, final_top_k=5)

    if not retrieved_chunks:
        return AskResponse(
            dataset_id=dataset_id,
            question=question,
            route_used="rag",
            explanation="No relevant business context or document chunks were found. Please upload a business glossary, schema notes, or context document (.pdf/.txt) first.",
            sql=None,
            results=[],
            row_count=0,
            retrieved_chunks=[]
        )

    # Build context string with clean document references
    context_blocks = []
    for idx, chk in enumerate(retrieved_chunks, 1):
        context_blocks.append(
            f"Reference [{idx}] - Document: {chk.source_doc} (Page {chk.page_number}):\n\"{chk.text}\""
        )
    context_str = "\n\n".join(context_blocks)

    prompt = f"""You are a Senior Business Intelligence & Domain Knowledge Analyst assistant.
Synthesize a clear, structured, and professional answer to the user's question using ONLY the provided business context references below.

Rules:
1. Provide a direct, professional answer (2-4 bullet points or clean paragraphs).
2. Explicitly cite the document reference at the end of key statements, e.g., `[Source: {retrieved_chunks[0].source_doc}, p.{retrieved_chunks[0].page_number}]`.
3. Do NOT include raw markdown asterisks in a messy way; format key terms cleanly using bold tags.
4. If the context does not contain enough information to answer the question, state that clearly.

Business Context References:
{context_str}

User Question: "{question}"
Answer:"""

    if not settings.GROQ_API_KEY:
        explanation_text = f"Retrieved {len(retrieved_chunks)} relevant context chunks. (GROQ_API_KEY is not set for synthesis)."
    else:
        from app.services.nl2sql import call_groq_with_retry
        client = Groq(api_key=settings.GROQ_API_KEY)
        resp = call_groq_with_retry(
            client,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        explanation_text = resp.choices[0].message.content or "No answer synthesized."

    return AskResponse(
        dataset_id=dataset_id,
        question=question,
        route_used="rag",
        explanation=explanation_text,
        sql=None,
        results=[],
        row_count=0,
        retrieved_chunks=retrieved_chunks
    )
