"""
Safety Guardrails Service
Detects prompt injection attempts, SQL injection risks, and sanitizes input/output text.
"""

import re
from typing import Tuple

PROMPT_INJECTION_PATTERNS = [
    r'ignore (all )?(previous|above) instructions',
    r'disregard (all )?prior rules',
    r'reveal (your )?system prompt',
    r'show (me )?system instructions',
    r'you are now in developer mode',
    r'jailbreak',
    r'<script\b[^>]*>',
]

DANGEROUS_SQL_PATTERNS = [
    r'\bdrop\s+table\b',
    r'\bdelete\s+from\b',
    r'\btruncate\s+table\b',
    r'\balter\s+table\b',
    r'\bupdate\s+.*\s+set\b',
    r'\binsert\s+into\b',
    r';\s*drop\b',
]

def validate_input_guardrails(question: str) -> Tuple[bool, str]:
    """
    Validates user input against prompt injection and malicious commands.
    Returns (is_valid, error_reason).
    """
    q_lower = question.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, q_lower):
            return False, "Input contains unauthorized system manipulation patterns. Please ask a valid business or data query."

    for pattern in DANGEROUS_SQL_PATTERNS:
        if re.search(pattern, q_lower):
            return False, "Data modification commands (DROP, DELETE, UPDATE) are prohibited. Please ask read-only analytical questions."

    return True, ""

def sanitize_output_guardrails(text: str) -> str:
    """
    Sanitizes LLM outputs to prevent exposing raw API keys or internal environment variables.
    """
    if not text:
        return ""
    # Mask any potential API key patterns (e.g. gsk_...)
    sanitized = re.sub(r'gsk_[a-zA-Z0-9_-]{20,}', '[MASKED_KEY]', text)
    return sanitized
