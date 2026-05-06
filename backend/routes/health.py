import torch
from fastapi import APIRouter

from schemas import HealthResponse
from services.model_service import model_service
from services.xai_service import xai_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    vram = xai_service.get_vram_info()
    return {
        "status"        : "operational",
        "models_loaded" : model_service.loaded,
        "qwen_loaded"   : xai_service.loaded,
        "gpu_available" : torch.cuda.is_available(),
        "gpu_vram_used" : vram.get("used_gb"),
        "gpu_vram_total": vram.get("total_gb"),
    }
