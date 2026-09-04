"""
Unit tests for SQL prompt formatting and SQL extraction logic.
"""

from app.services.nl2sql import extract_sql_from_response, generate_sql_prompt

def test_extract_sql_from_markdown():
    llm_output = "Here is the query:\n```sql\nSELECT category, SUM(sales) FROM tbl_sales GROUP BY category;\n```"
    extracted = extract_sql_from_response(llm_output)
    assert extracted == "SELECT category, SUM(sales) FROM tbl_sales GROUP BY category;"

def test_extract_sql_plain_select():
    llm_output = "SELECT * FROM tbl_data LIMIT 5"
    extracted = extract_sql_from_response(llm_output)
    assert extracted == "SELECT * FROM tbl_data LIMIT 5"

def test_generate_sql_prompt():
    schema = [{"column": "sales", "type": "DOUBLE"}, {"column": "region", "type": "VARCHAR"}]
    sample_rows = [{"sales": 100, "region": "North"}]
    prompt = generate_sql_prompt("tbl_test", schema, sample_rows, "What are total sales by region?")
    
    assert "tbl_test" in prompt
    assert "sales: DOUBLE" in prompt
    assert "What are total sales by region?" in prompt
