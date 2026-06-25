from fastapi import APIRouter

from schemas import HealthResponse
from services.model_service import model_service
from services.xai_service import xai_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    return {
        "status"       : "operational",
        "models_loaded": model_service.loaded,
        "xai_loaded"   : xai_service.loaded,
    }
