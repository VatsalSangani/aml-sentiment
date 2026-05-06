import time

from fastapi import APIRouter, HTTPException

from schemas import TransactionRequest, AnalyzeResponse
from services.model_service import model_service
from services.xai_service import xai_service
from db.monitor import log_prediction

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: TransactionRequest):
    try:
        t_start = time.time()

        result = model_service.predict(req)

        explanation = xai_service.explain(
            risk_score   = result["risk_score"],
            features     = result["features"],
            shap_drivers = result["shap_drivers"],
        )

        total_ms = int((time.time() - t_start) * 1000)
        log_prediction(req, result, total_ms)

        return {**result, "explanation": explanation, "processing_ms": total_ms}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
