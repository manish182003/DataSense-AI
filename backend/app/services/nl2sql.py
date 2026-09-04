"""
NL2SQL Service
Uses Groq API to translate natural language questions into DuckDB SQL,
executes the query with 1-shot self-correction retry on execution errors, and generates 
plain-language explanations with safe payload truncation and exponential backoff retry.
"""

import re
import time
import logging
from typing import Dict, Any, List
from groq import Groq
from app.core.config import settings
from app.core.database import get_table_schema, execute_query
from app.schemas.payload import AskResponse

logger = logging.getLogger(__name__)

def extract_sql_from_response(text: str) -> str:
    """
    Extracts executable SQL string from LLM markdown code blocks or plain text output.
    Cleans leading/trailing markdown code blocks and annotations.
    """
    sql_match = re.search(r'```sql\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        sql = sql_match.group(1).strip()
    else:
        code_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if code_match:
            sql = code_match.group(1).strip()
        else:
            sql = text.strip()

    # Clean up any residual markdown backtick headers
    sql = re.sub(r'^```(sql)?\s*', '', sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r'\s*```$', '', sql).strip()
    
    return sql

def call_groq_with_retry(client: Groq, messages: List[Dict[str, str]], model: str = None, temperature: float = 0.1, retries: int = 3):
    """
    Executes Groq chat completion with exponential backoff on HTTP 429 rate limits 
    and fallback model strategy.
    """
    primary_model = model or settings.DEFAULT_LLM_MODEL
    fallback_model = "openai/gpt-oss-20b"

    for attempt in range(retries):
        try:
            return client.chat.completions.create(
                model=primary_model,
                messages=messages,
                temperature=temperature
            )
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower():
                logger.warning(f"Groq Rate Limit (429) hit on attempt {attempt+1}/{retries}. Backing off.")
                time.sleep(2.0 * (attempt + 1))
            elif attempt == retries - 1:
                # Try fallback lightweight model on final retry
                try:
                    logger.warning(f"Attempting fallback model '{fallback_model}' due to error: {err_str}")
                    return client.chat.completions.create(
                        model=fallback_model,
                        messages=messages,
                        temperature=temperature
                    )
                except Exception:
                    pass
                raise e
            else:
                time.sleep(1.0)

def generate_sql_prompt(table_name: str, schema: List[Dict[str, str]], sample_rows: List[Dict[str, Any]], question: str) -> str:
    """
    Constructs a structured prompt containing schema and sample rows for the LLM.
    Safely truncates schema and sample rows to prevent prompt size issues on wide datasets.
    """
    schema_str = "\n".join([f"  - {item['column']}: {item['type']}" for item in schema[:50]])
    if len(schema) > 50:
        schema_str += f"\n  - ... ({len(schema) - 50} additional columns omitted for prompt brevity)"
    
    sample_str = ""
    if sample_rows:
        raw_sample = str(sample_rows[:2])
        if len(raw_sample) > 1500:
            raw_sample = raw_sample[:1500] + "... [truncated]"
        sample_str = "Sample Data:\n" + raw_sample

    prompt = f"""You are an expert SQL engineer for DuckDB.
Generate a valid, read-only DuckDB SQL query to answer the user's natural language question.

Database Schema:
Table Name: {table_name}
Columns:
{schema_str}

{sample_str}

CRITICAL DUCKDB SYNTAX RULES:
1. Output ONLY the raw SQL query inside a markdown code block (```sql ... ```).
2. Do NOT execute drop, alter, update, or delete commands. Use read-only SELECT statements.
3. DuckDB does NOT support TO_DATE(), STR_TO_DATE(), or DATE_FORMAT().
   - For string-to-date conversion, use `TRY_CAST(col AS DATE)` or `strptime(col, '%Y-%m-%d')`.
   - For date truncation, use `date_trunc('month', TRY_CAST(col AS DATE))`.
4. Ensure column names match the schema EXACTLY.
5. If the user asks about important features, targets, or default prediction, query key column metrics, counts, or target column distributions.

User Question: "{question}"
SQL Query:"""
    return prompt

def generate_explanation_prompt(question: str, sql: str, results: List[Dict[str, Any]], schema: List[Dict[str, str]] = None) -> str:
    """
    Constructs prompt to convert SQL query results into a plain-language summary for non-technical users.
    Safely truncates results payload to prevent Groq HTTP 413 Payload Too Large errors.
    """
    results_str = str(results[:5])
    if len(results_str) > 2000:
        results_str = results_str[:2000] + "... [truncated for length]"

    schema_info = ""
    if schema:
        col_names = [item['column'] for item in schema[:25]]
        schema_info = "Dataset Columns Available: " + ", ".join(col_names)
    
    prompt = f"""You are a helpful Data Analyst assistant.
Synthesize the SQL query results and dataset context into a clear, structured, and professional plain-language summary for the user.

User Question: "{question}"
Executed SQL: {sql}
{schema_info}
Query Result Summary (showing top {min(len(results), 5)} rows):
{results_str}

Rules:
1. Provide a direct, informative answer to the user's question.
2. If the user asks about prediction targets or feature relevance (e.g. customer default), identify key target/feature columns from the schema and summarize their distribution and analytical significance.
3. Keep the response clean and well-formatted using standard markdown bullet points or GFM markdown tables (`| Col1 | Col2 |`).
4. Do NOT output Python code blocks, Matplotlib code, or pseudo-code (e.g. `import matplotlib.pyplot`). Provide pure plain-language insights; the UI automatically generates interactive Plotly graphs.
5. Do NOT output raw `<br>` HTML tags inside tables or text. Use standard markdown line breaks or bullet points."""
    return prompt

def ask_nl2sql(dataset_id: str, question: str, sample_rows: List[Dict[str, Any]] = None) -> AskResponse:
    """
    Main entry point for NL2SQL question answering flow with 1-shot self-correction and safe fallback execution.
    """
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Please configure your .env file with a valid Groq API key.")

    client = Groq(api_key=settings.GROQ_API_KEY)
    schema = get_table_schema(dataset_id)
    
    if not sample_rows:
        try:
            sample_rows = execute_query(f"SELECT * FROM {dataset_id} LIMIT 2")
        except Exception:
            sample_rows = []

    # Check for explicit dataset overview questions
    q_lower = question.lower()
    is_overview_query = any(k in q_lower for k in [
        'tell me about data', 'tell me about dataset', 'what is in data', 
        'what is in dataset', 'describe data', 'overview of data', 'summary of dataset'
    ])

    if is_overview_query:
        sql_query = f"SELECT * FROM {dataset_id} LIMIT 10"
    else:
        # Step 1: Request SQL from Groq LLM with backoff retry
        initial_prompt = generate_sql_prompt(dataset_id, schema, sample_rows, question)
        response = call_groq_with_retry(
            client,
            messages=[{"role": "user", "content": initial_prompt}],
            temperature=0.1
        )
        raw_llm_output = response.choices[0].message.content or ""
        sql_query = extract_sql_from_response(raw_llm_output)

    results = []
    # Step 2: Try executing SQL on DuckDB (with 1-shot self-correction loop)
    try:
        results = execute_query(sql_query)
    except Exception as err:
        error_msg = str(err)
        logger.warning(f"Initial SQL execution failed: {error_msg}. Attempting self-correction retry.")
        
        hint = ""
        if "to_date" in error_msg.lower() or "scalar function" in error_msg.lower():
            hint = "\nIMPORTANT HINT: DuckDB does NOT support TO_DATE(). Use `TRY_CAST(column_name AS DATE)` or `strptime(column_name, '%Y-%m-%d')` instead."

        retry_prompt = f"""The previous DuckDB SQL query failed with an execution error.

User Question: "{question}"
Table Name: {dataset_id}
Failed SQL: {sql_query}
Error Message: {error_msg}{hint}

Please fix the SQL query according to DuckDB syntax standards. Output ONLY valid SQL in ```sql ... ``` block."""
        
        try:
            retry_response = call_groq_with_retry(
                client,
                messages=[{"role": "user", "content": retry_prompt}],
                temperature=0.1
            )
            retry_output = retry_response.choices[0].message.content or ""
            sql_query = extract_sql_from_response(retry_output)
            results = execute_query(sql_query)
        except Exception as retry_err:
            logger.error(f"SQL Self-Correction retry failed: {retry_err}")
            # Failsafe fallback: if retry fails, execute top 5 rows select query
            sql_query = f"SELECT * FROM {dataset_id} LIMIT 5"
            results = execute_query(sql_query)

    # Step 3: Synthesize plain-language explanation safely
    explanation_prompt = generate_explanation_prompt(question, sql_query, results, schema)
    explanation_resp = call_groq_with_retry(
        client,
        messages=[{"role": "user", "content": explanation_prompt}],
        temperature=0.2
    )
    explanation_text = explanation_resp.choices[0].message.content or "No explanation generated."

    return AskResponse(
        dataset_id=dataset_id,
        question=question,
        sql=sql_query,
        explanation=explanation_text,
        results=results,
        row_count=len(results)
    )
