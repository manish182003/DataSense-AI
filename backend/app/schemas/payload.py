"""
Pydantic Schemas for Request & Response Validation
Clean, strongly-typed contracts for DataSense API endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ColumnMetadata(BaseModel):
    name: str
    dtype: str
    missing_count: int
    missing_percentage: float

class DatasetMetadata(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    total_missing_percentage: float
    columns: List[ColumnMetadata]
    sample_rows: List[Dict[str, Any]]

class ProfileChart(BaseModel):
    chart_id: str
    title: str
    chart_type: str
    plotly_spec: Dict[str, Any]

class ProfileResponse(BaseModel):
    dataset_id: str
    summary_stats: Dict[str, Any]
    charts: List[ProfileChart]

class AskRequest(BaseModel):
    dataset_id: str
    question: str
    mode: Optional[str] = Field(default="auto", description="Routing mode: 'auto', 'nl2sql', or 'rag'")

class RetrievedChunk(BaseModel):
    chunk_id: str
    source_doc: str
    page_number: Optional[int] = 1
    text: str
    rrf_score: float
    rerank_score: float

class AskResponse(BaseModel):
    dataset_id: str
    question: str
    route_used: str = Field(default="nl2sql", description="Route taken: 'nl2sql' or 'rag'")
    sql: Optional[str] = None
    explanation: str
    results: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = 0
    retrieved_chunks: Optional[List[RetrievedChunk]] = None

class ContextUploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks_created: int
    total_characters: int

class ContextDocSummary(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int

