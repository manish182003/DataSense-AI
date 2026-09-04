"""
DuckDB Database Manager
Provides connection management and helper functions for running SQL queries against tabular datasets.
"""

import duckdb
import pandas as pd
from typing import List, Dict, Any
from app.core.config import settings

import time

def get_db_connection(max_retries: int = 5, delay: float = 0.5):
    """
    Returns a connection to the persistent DuckDB database file with retry on process lock contention.
    """
    for attempt in range(max_retries):
        try:
            return duckdb.connect(settings.DUCKDB_PATH)
        except duckdb.IOException as err:
            if "used by another process" in str(err) and attempt < max_retries - 1:
                time.sleep(delay)
                continue
            raise err

def register_dataframe(table_name: str, df: pd.DataFrame):
    """
    Registers a pandas DataFrame as a table inside DuckDB database.
    Overwrites table if it already exists.
    """
    conn = get_db_connection()
    try:
        # Create or replace table directly from pandas DataFrame
        conn.register("df_temp", df)
        conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df_temp")
        conn.unregister("df_temp")
    finally:
        conn.close()

def execute_query(sql_query: str) -> List[Dict[str, Any]]:
    """
    Executes a SQL query against DuckDB and returns the result as a list of dictionaries.
    """
    conn = get_db_connection()
    try:
        rel = conn.execute(sql_query)
        df_result = rel.df()
        
        # Replace NaN values with None for proper JSON serialization
        df_result = df_result.where(pd.notnull(df_result), None)
        return df_result.to_dict(orient="records")
    finally:
        conn.close()

def get_table_schema(table_name: str) -> List[Dict[str, str]]:
    """
    Retrieves column names and data types for a table.
    """
    conn = get_db_connection()
    try:
        schema_info = conn.execute(f"DESCRIBE {table_name}").fetchall()
        # Returns list of dicts with column_name and data_type
        return [{"column": row[0], "type": row[1]} for row in schema_info]
    finally:
        conn.close()
