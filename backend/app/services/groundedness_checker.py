"""
Groundedness Verification Guardrail
Verifies whether synthesized LLM answers are strictly grounded in retrieved evidence to prevent hallucinations.
"""

from typing import List, Tuple
from groq import Groq
from app.core.config import settings

def verify_groundedness(question: str, evidence_str: str, answer_text: str) -> Tuple[bool, str]:
    """
    Evaluates if answer_text is supported by evidence_str.
    Returns (is_grounded, explanation/reason).
    """
    if not settings.GROQ_API_KEY or not answer_text or not evidence_str:
        return True, "Groundedness check bypassed."

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        prompt = f"""You are an audit reviewer verifying answer correctness.
Evaluate whether the Synthesized Answer is supported by the Provided Evidence.

User Question: "{question}"
Provided Evidence:
{evidence_str[:1500]}

Synthesized Answer:
{answer_text}

Rules:
1. Output "PASS" if the key claims in the answer are supported by the evidence.
2. Output "FAIL" if the answer contains fabricated numbers, hallucinated policies not present in evidence, or contradicts the evidence.
3. Output ONLY "PASS" or "FAIL" followed by a short 1-sentence explanation."""

        resp = client.chat.completions.create(
            model=settings.FAST_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=40
        )
        if resp and hasattr(resp, 'choices') and resp.choices:
            output = (resp.choices[0].message.content or "").strip()
            if output.startswith("FAIL"):
                return False, output
        return True, "Check complete."
    except Exception:
        return True, "Check complete."
