"""
Intent Router Service
Determines whether a user's question should be routed to the NL2SQL database engine or the Hybrid RAG context engine.
"""

import re
from groq import Groq
from app.core.config import settings

def route_intent(question: str) -> str:
    """
    Classifies a user question as 'nl2sql' or 'rag'.
    """
    q_lower = question.lower()
    # Explicit override for dataset summary/overview queries
    data_overview_keywords = ['data', 'dataset', 'table', 'overview', 'summary', 'schema', 'record', 'column', 'rows', 'mrr', 'revenue', 'sales']
    if any(kw in q_lower for kw in ['what is in', 'tell me about', 'describe', 'summary of']) or any(kw in q_lower for kw in data_overview_keywords):
        if not any(k in q_lower for k in ['glossary', 'policy document', 'pdf note']):
            return "nl2sql"

    if not settings.GROQ_API_KEY:
        return _fallback_heuristic_route(question)

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        prompt = f"""You are an intent router classifier for a Data Analytics & Business Intelligence system.
Analyze the user's question and categorize it into EXACTLY ONE of two routes:
- "nl2sql": If the question asks about tabular data records, dataset summaries, column metrics, sales/revenue statistics, top records, or general data inquiries.
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
    except Exception as e:
        pass

    return _fallback_heuristic_route(question)

def _fallback_heuristic_route(question: str) -> str:
    q_lower = question.lower()
    rag_keywords = ['glossary', 'policy', 'document', 'pdf', 'definition of term']
    if any(re.search(r'\b' + re.escape(kw) + r'\b', q_lower) for kw in rag_keywords):
        return "rag"
    return "nl2sql"
