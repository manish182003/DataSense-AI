from fastapi import APIRouter, HTTPException
from app.services.evaluator import EvaluatorService

router = APIRouter(prefix="/api/eval", tags=["Evaluation"])
evaluator_service = EvaluatorService()

@router.get("/run")
async def run_evaluation():
    """Runs automated evaluation suite across golden benchmark dataset."""
    try:
        results = evaluator_service.run_full_evaluation()
        return {
            "success": True,
            "metrics": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
