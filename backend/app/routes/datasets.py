"""
Dataset Ingestion Routes
Endpoints for uploading dataset files (CSV/Excel/JSON) and querying dataset metadata.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import Dict
import pandas as pd

from app.schemas.payload import DatasetMetadata
from app.services.ingestion import process_file_upload

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])

# In-memory dictionary cache for active datasets: dataset_id -> (metadata, df)
DATASET_STORE: Dict[str, Dict] = {}

import os
import uuid
from app.core.config import settings

@router.post("/upload", response_model=DatasetMetadata, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload a CSV, Excel, or JSON dataset.
    Streams large dataset uploads in 1MB chunks to disk to keep RAM memory usage flat (<5MB).
    """
    filename = file.filename or "uploaded_file.csv"
    file_ext = os.path.splitext(filename)[1].lower()
    
    temp_dir = settings.UPLOAD_DIR
    os.makedirs(temp_dir, exist_ok=True)
    temp_filepath = os.path.join(temp_dir, f"upload_{uuid.uuid4().hex[:8]}{file_ext}")
    
    try:
        with open(temp_filepath, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        table_name, metadata, df = process_file_upload(temp_filepath, filename)
        # Store in dataset cache for fast profiling access
        DATASET_STORE[table_name] = {
            "metadata": metadata,
            "df": df
        }
        import gc
        gc.collect()
        return metadata
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to process dataset: {str(err)}")

def get_dataset_entry(dataset_id: str) -> Dict:
    if dataset_id in DATASET_STORE:
        return DATASET_STORE[dataset_id]
    
    # Check if table exists in DuckDB persistent store
    try:
        from app.core.database import get_table_schema, get_db_connection
        schema = get_table_schema(dataset_id)
        if schema:
            conn = get_db_connection()
            total_rows = conn.execute(f"SELECT COUNT(*) FROM {dataset_id}").fetchone()[0]
            schema_info = conn.execute(f"DESCRIBE {dataset_id}").fetchall()
            total_cols = len(schema_info)
            total_cells = total_rows * total_cols
            
            column_meta_list = []
            if schema_info and total_rows > 0:
                null_exprs = [f'COUNT(*) - COUNT("{c[0]}")' for c in schema_info]
                null_counts_row = conn.execute(f"SELECT {', '.join(null_exprs)} FROM {dataset_id}").fetchone()
                for idx, col_tuple in enumerate(schema_info):
                    col_name = col_tuple[0]
                    col_type = col_tuple[1]
                    col_nulls = int(null_counts_row[idx]) if null_counts_row else 0
                    col_null_pct = round((col_nulls / total_rows * 100) if total_rows > 0 else 0, 2)
                    column_meta_list.append(ColumnMetadata(
                        name=col_name,
                        dtype=str(col_type),
                        missing_count=col_nulls,
                        missing_percentage=col_null_pct
                    ))

            total_missing = sum(c.missing_count for c in column_meta_list)
            total_missing_pct = round((total_missing / total_cells * 100) if total_cells > 0 else 0, 2)

            df = conn.execute(f"SELECT * FROM {dataset_id} LIMIT 5000").df()
            conn.close()

            sample_df = df.head(5).where(pd.notnull(df.head(5)), None)
            sample_rows = sample_df.to_dict(orient="records")

            metadata = DatasetMetadata(
                dataset_id=dataset_id,
                filename=dataset_id,
                row_count=total_rows,
                column_count=total_cols,
                total_missing_percentage=total_missing_pct,
                columns=column_meta_list,
                sample_rows=sample_rows
            )
            entry = {"metadata": metadata, "df": df}
            DATASET_STORE[dataset_id] = entry
            return entry
    except Exception:
        pass
    return None

@router.get("/{dataset_id}", response_model=DatasetMetadata)
async def get_dataset_metadata(dataset_id: str):
    """
    Retrieve metadata for a previously uploaded dataset.
    """
    entry = get_dataset_entry(dataset_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload dataset first.")
    return entry["metadata"]

