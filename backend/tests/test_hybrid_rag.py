"""
Tests for Phase 2 Hybrid RAG System
Verifies document parsing, chunking, FAISS dense retrieval, BM25 sparse retrieval,
RRF fusion, Cross-Encoder reranking, and Intent Routing.
"""

import pytest
from app.services.context_store import ContextStore
from app.services.intent_router import route_intent, _fallback_heuristic_route

def test_context_store_chunking_and_indexing():
    store = ContextStore()
    
    sample_text = """
    Business Definition: ARR stands for Annual Recurring Revenue. 
    It is computed by summing the annualized value of all active subscription contracts.
    
    Churn Rate Definition: Churn rate is the percentage of customers that cancel their subscription within a given time period.
    """
    
    res = store.add_document(sample_text.encode('utf-8'), "business_glossary.txt")
    assert res["chunks_created"] > 0
    assert "doc_id" in res
    assert len(store.chunks) > 0

    # Execute Hybrid Search
    query = "What does ARR stand for?"
    results = store.hybrid_search(query, final_top_k=3)
    
    assert len(results) > 0
    top_result = results[0]
    assert "ARR" in top_result.text
    assert top_result.source_doc == "business_glossary.txt"
    assert top_result.rrf_score > 0

def test_intent_router_heuristics():
    # RAG questions
    assert _fallback_heuristic_route("What is the definition of ARR in the glossary?") == "rag"
    assert _fallback_heuristic_route("Explain the churn rate policy") == "rag"
    
    # NL2SQL questions
    assert _fallback_heuristic_route("What are total sales by category?") == "nl2sql"
    assert _fallback_heuristic_route("Show me top 5 revenue transactions") == "nl2sql"
