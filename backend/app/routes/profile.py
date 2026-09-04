"""
Profile Routes
Endpoint for retrieving auto-generated statistics and Plotly visualization specifications.
"""

from fastapi import APIRouter, HTTPException
from app.schemas.payload import ProfileResponse
from app.routes.datasets import get_dataset_entry
from app.services.profiler import build_dataset_profile

router = APIRouter(prefix="/api/datasets", tags=["Profiling"])

@router.get("/{dataset_id}/profile", response_model=ProfileResponse)
async def get_dataset_profile(dataset_id: str):
    """
    Returns column statistics and 4-6 Plotly figure specifications for rendering dynamic charts.
    """
    entry = get_dataset_entry(dataset_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload dataset first.")
    
    df = entry["df"]
    try:
        profile_data = build_dataset_profile(dataset_id, df)
        return profile_data
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Profiling failed: {str(err)}")
