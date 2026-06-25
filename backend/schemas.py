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

    # ── Optional advanced/graph fields ─────────────────────────
    # Surfaced via the dashboard's "Show advanced fields" toggle.
    # When omitted, the model falls back to representative defaults
    # (see model_service.build_features) since this ad-hoc endpoint
    # has no access to the full transaction graph.
    hour_of_day : Optional[int]  = Field(default=None, ge=0, le=23, example=14)
    is_in_cycle : Optional[bool] = Field(default=None, example=False)
    fan_in      : Optional[int]  = Field(default=None, ge=1, example=3)

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
    xai_loaded    : bool