"""
Intent Router Service
Determines whether a user's question should be routed to the NL2SQL database engine or the Hybrid RAG context engine.
"""

import re
from groq import Groq
from app.core.config import settings

def route_intent(question: str, dataset_id: str = None) -> str:
    """
    Classifies a user question as 'nl2sql' or 'rag'.
    Prioritizes 'nl2sql' whenever dataset analytics keywords are detected.
    """
    q_lower = question.lower()
    
    # 1. Explicit business policy / documentation keywords force RAG
    explicit_rag_keywords = ['glossary', 'policy', 'policy document', 'pdf note', 'company rule', 'return policy', 'pdf']
    if any(kw in q_lower for kw in explicit_rag_keywords):
        return "rag"

    # 2. Explicit data analytics & tabular dataset keywords force NL2SQL
    data_analytics_keywords = [
        'month', 'monthly', 'year', 'yearly', 'date', 'sales', 'revenue', 'profit', 
        'count', 'total', 'average', 'sum', 'top', 'highest', 'lowest', 'by', 
        'trend', 'chart', 'graph', 'dataset', 'table', 'rows', 'column', 'region',
        'sub-category', 'category', 'customer', 'amount', 'distribution', 'rate'
    ]
    if any(kw in q_lower for kw in data_analytics_keywords):
        return "nl2sql"

    # General overview phrases
    if any(kw in q_lower for kw in ['what is in', 'tell me about', 'describe', 'summary of', 'show me']):
        return "nl2sql"

    if not settings.GROQ_API_KEY:
        return _fallback_heuristic_route(question)

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        prompt = f"""You are an intent router classifier for a Data Analytics & Business Intelligence system.
Analyze the user's question and categorize it into EXACTLY ONE of two routes:
- "nl2sql": If the question asks about tabular data records, dataset summaries, column metrics, sales/revenue statistics, top records, time trends, or general data inquiries.
- "rag": ONLY if the question asks for external business glossary definitions, policy text documents, or uploaded PDF documentation notes.

Question: "{question}"

Output ONLY "nl2sql" or "rag" (no punctuation, no additional text)."""

        resp = client.chat.completions.create(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=5
        )
        output = (resp.choices[0].message.content or "").strip().lower()
        if "rag" in output:
            return "rag"
        if "sql" in output or "nl2sql" in output:
            return "nl2sql"
    except Exception:
        pass

    return _fallback_heuristic_route(question)

def _fallback_heuristic_route(question: str) -> str:
    q_lower = question.lower()
    rag_keywords = ['glossary', 'policy', 'document', 'pdf', 'definition of term']
    if any(re.search(r'\b' + re.escape(kw) + r'\b', q_lower) for kw in rag_keywords):
        return "rag"
    return "nl2sql"
