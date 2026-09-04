"""
Ingestion Service
Parses uploaded datasets (CSV, Excel, JSON), infers datatypes, computes metadata, 
and persists tables into DuckDB.
"""

import os
import re
import uuid
import pandas as pd
from typing import Tuple
from app.core.database import register_dataframe
from app.schemas.payload import DatasetMetadata, ColumnMetadata

def sanitize_table_name(filename: str) -> str:
    """
    Converts a filename into a clean SQL-compatible table name.
    Example: 'Sales Data 2024.csv' -> 'tbl_sales_data_2024_<short_hash>'
    """
    base_name = os.path.splitext(filename)[0]
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', base_name).lower()
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    short_uid = uuid.uuid4().hex[:6]
    return f"tbl_{clean_name}_{short_uid}"

def sanitize_column_name(col_name: str) -> str:
    """
    Sanitizes column header names for seamless DuckDB SQL queries.
    """
    col_str = str(col_name).strip()
    clean_col = re.sub(r'[^a-zA-Z0-9_]', '_', col_str).lower()
    clean_col = re.sub(r'_+', '_', clean_col).strip('_')
    return clean_col if clean_col else "unnamed_column"

def process_file_upload(file_bytes: bytes, filename: str) -> Tuple[str, DatasetMetadata, pd.DataFrame]:
    """
    Reads file content, sanitizes headers, loads into DuckDB, and generates metadata.
    """
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Parse file into pandas DataFrame based on extension
    if file_ext == '.csv':
        df = pd.read_csv(pd.io.common.BytesIO(file_bytes))
    elif file_ext in ['.xlsx', '.xls']:
        df = pd.read_excel(pd.io.common.BytesIO(file_bytes))
    elif file_ext == '.json':
        df = pd.read_json(pd.io.common.BytesIO(file_bytes))
    else:
        raise ValueError(f"Unsupported file extension: {file_ext}. Allowed: .csv, .xlsx, .xls, .json")

    if df.empty:
        raise ValueError("The uploaded dataset file is empty.")

    # Sanitize column names
    df.columns = [sanitize_column_name(c) for c in df.columns]

    # Attempt to convert object columns to datetime if suitable
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                # Try parsing as datetime if string looks like date
                sample_vals = df[col].dropna().astype(str).head(20)
                if any(re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', v) for v in sample_vals):
                    df[col] = pd.to_datetime(df[col], errors='ignore')
            except Exception:
                pass

    # Generate SQL table name and register in DuckDB
    table_name = sanitize_table_name(filename)
    register_dataframe(table_name, df)

    # Compute dataset metadata
    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols
    total_missing = int(df.isnull().sum().sum())
    total_missing_pct = round((total_missing / total_cells * 100) if total_cells > 0 else 0, 2)

    column_meta_list = []
    for col in df.columns:
        col_nulls = int(df[col].isnull().sum())
        col_null_pct = round((col_nulls / total_rows * 100) if total_rows > 0 else 0, 2)
        column_meta_list.append(ColumnMetadata(
            name=col,
            dtype=str(df[col].dtype),
            missing_count=col_nulls,
            missing_percentage=col_null_pct
        ))

    # Prepare sample rows (first 5)
    sample_df = df.head(5).where(pd.notnull(df.head(5)), None)
    sample_rows = sample_df.to_dict(orient="records")

    metadata = DatasetMetadata(
        dataset_id=table_name,
        filename=filename,
        row_count=total_rows,
        column_count=total_cols,
        total_missing_percentage=total_missing_pct,
        columns=column_meta_list,
        sample_rows=sample_rows
    )

    return table_name, metadata, df
