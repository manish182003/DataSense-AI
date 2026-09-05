"""
Query Processor Engine
Handles query expansion, rewriting, and multi-part decomposition.
"""

import re
from typing import List, Dict, Any
from groq import Groq
from app.core.config import settings

ACRONYM_EXPANSIONS = {
    r'\barr\b': 'Annual Recurring Revenue (ARR)',
    r'\bmrr\b': 'Monthly Recurring Revenue (MRR)',
    r'\bcsat\b': 'Customer Satisfaction (CSAT)',
    r'\bkpi\b': 'Key Performance Indicator (KPI)',
    r'\byoy\b': 'Year over Year (YoY)',
    r'\bmom\b': 'Month over Month (MoM)',
    r'\bsla\b': 'Service Level Agreement (SLA)',
}

def expand_query(query: str) -> str:
    """
    Expands common acronyms and normalizes user query.
    """
    expanded = query.strip()
    for pattern, replacement in ACRONYM_EXPANSIONS.items():
        expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
    return expanded

def rewrite_query_for_search(query: str) -> str:
    """
    Rewrites user query into an optimized vector search string.
    """
    expanded = expand_query(query)
    if not settings.GROQ_API_KEY or len(expanded.split()) < 4:
        return expanded

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        prompt = f"""Rewrite the following user search query into a clear, concise, and keyword-rich statement optimized for semantic document search.

Original Query: "{query}"

Rules:
1. Output ONLY the rewritten search statement (1 sentence, no quotes, no extra text).
2. Expand abbreviations and include key domain synonyms."""

        resp = client.chat.completions.create(
            model=settings.FAST_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=30
        )
        if resp and hasattr(resp, 'choices') and resp.choices:
            rewritten = (resp.choices[0].message.content or "").strip()
            return rewritten if rewritten else expanded
        return expanded
    except Exception:
        return expanded

def decompose_query(query: str) -> List[str]:
    """
    Decomposes multi-part questions into sub-queries.
    """
    expanded = expand_query(query)
    # Check for conjunctions like "and also", "as well as", "plus"
    parts = re.split(r'\b(and also|as well as|\band\b|\bplus\b|\balso\b)\b', expanded, flags=re.IGNORECASE)
    sub_queries = [p.strip() for p in parts if p.strip() and p.lower() not in ['and also', 'as well as', 'and', 'plus', 'also']]
    
    if len(sub_queries) > 1 and all(len(sq.split()) >= 2 for sq in sub_queries):
        return sub_queries
    return [expanded]
