from fastapi import APIRouter, Depends

from services.xai_service import xai_service
from security import require_api_key

router = APIRouter(prefix="/xai")


@router.post("/unload")
async def unload_xai(_auth=Depends(require_api_key)):
    """Manually release the XAI client when not needed."""
    if not xai_service.loaded:
        return {"message": "XAI service is not loaded"}
    xai_service.unload()
    return {"message": "XAI service unloaded"}


@router.get("/status")
async def xai_status():
    vram = xai_service.get_vram_info()
    return {
        "loaded"  : xai_service.loaded,
        "model_id": "gpt-4o-mini",
        "provider": "OpenAI",
        "vram"    : vram,
    }
