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

@router.post("/upload", response_model=DatasetMetadata, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload a CSV, Excel, or JSON dataset.
    Parses file, infers data types, stores table in DuckDB, and returns summary metadata.
    """
    filename = file.filename or "uploaded_file.csv"
    file_bytes = await file.read()
    
    try:
        table_name, metadata, df = process_file_upload(file_bytes, filename)
        # Store in dataset cache for fast profiling access
        DATASET_STORE[table_name] = {
            "metadata": metadata,
            "df": df
        }
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
            df = conn.execute(f"SELECT * FROM {dataset_id}").df()
            conn.close()
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

