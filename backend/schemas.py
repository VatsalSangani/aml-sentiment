from pydantic import BaseModel, Field
from typing import Optional

# ── Request ────────────────────────────────────────────────────
class TransactionRequest(BaseModel):
    payment_format : str   = Field(..., example="ACH")
    amount         : float = Field(..., gt=0, example=9500.0)
    from_bank      : str   = Field(..., example="BANK_A")
    to_bank        : str   = Field(..., example="BANK_B")
    currency       : str   = Field(..., example="US Dollar")
    fan_out        : int   = Field(..., ge=1, example=12)
    tx_velocity    : int   = Field(..., ge=1, example=45)

# ── SHAP driver item ───────────────────────────────────────────
class ShapDriver(BaseModel):
    feature   : str
    shap_val  : float
    direction : str   # "increases" or "decreases"

# ── Response ───────────────────────────────────────────────────
class AnalyzeResponse(BaseModel):
    risk_score   : float
    verdict      : str         # "FLAGGED" or "CLEARED"
    threshold    : float
    shap_drivers : list[ShapDriver]
    features     : dict
    explanation  : str
    processing_ms: int

# ── Health response ────────────────────────────────────────────
class HealthResponse(BaseModel):
    status        : str
    models_loaded : bool
    qwen_loaded   : bool
    gpu_available : bool
    gpu_vram_used : Optional[float]
    gpu_vram_total: Optional[float]