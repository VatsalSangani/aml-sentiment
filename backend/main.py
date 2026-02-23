import os
import sys
import json
import time
import torch
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ── Add project root ───────────────────────────────────────────
PROJECT_ROOT = r"C:\Users\VatsaL\Desktop\Datasets\AML_Sentinel"
sys.path.insert(0, PROJECT_ROOT)
from config import MODELS_DIR, TRAINING_DIR

from schemas       import TransactionRequest, AnalyzeResponse, HealthResponse
from model_service import model_service
from xai_service   import xai_service

# ── App ────────────────────────────────────────────────────────
app = FastAPI(
    title       = "AML Sentinel API",
    description = "XGBoost + LightGBM Ensemble + Qwen 2.5 1.5B XAI",
    version     = "1.0.0"
)

# ── CORS — allow React dev server ──────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Load ML models on startup (not Qwen — that's on demand) ────
@app.on_event("startup")
async def startup():
    print("🚀 AML Sentinel API starting...")
    model_service.load()
    print("✅ Ready! Qwen will load on first /analyze request.")

# ══════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════

# ── Health check ───────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
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

# ── Transaction analysis — live Qwen explanation ───────────────
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: TransactionRequest):
    try:
        t_start = time.time()

        # 1. ML prediction + SHAP
        result = model_service.predict(req)

        # 2. Qwen explanation (loads on first call)
        explanation = xai_service.explain(
            risk_score   = result["risk_score"],
            features     = result["features"],
            shap_drivers = result["shap_drivers"]
        )

        total_ms = int((time.time() - t_start) * 1000)

        return {
            **result,
            "explanation"  : explanation,
            "processing_ms": total_ms
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Pre-generated XAI reports (30 cases) ──────────────────────
@app.get("/reports")
async def get_reports():
    """Return the pre-generated 30 XAI reports from JSON file."""
    xai_dir = os.path.join(TRAINING_DIR, "xai_reports")

    # Find the most recent JSON report
    json_files = sorted(Path(xai_dir).glob("xai_reports_*.json"),
                        reverse=True)
    if not json_files:
        raise HTTPException(
            status_code=404,
            detail="No XAI reports found. Run AML_XAI.ipynb first."
        )

    with open(json_files[0], "r", encoding="utf-8") as f:
        reports = json.load(f)

    return {"reports": reports, "count": len(reports)}

# ── Model performance stats ────────────────────────────────────
@app.get("/stats")
async def get_stats():
    """Return model evaluation stats from saved report."""
    report_path = os.path.join(MODELS_DIR, "evaluation_report.txt")
    weights_path = os.path.join(MODELS_DIR, "ensemble_weights.json")

    if not os.path.exists(weights_path):
        raise HTTPException(status_code=404,
                            detail="ensemble_weights.json not found.")

    with open(weights_path, "r") as f:
        weights = json.load(f)

    return {
        "auc_roc"          : 0.9857,
        "auc_pr"           : 0.3857,
        "recall"           : 0.8123,
        "precision"        : 0.0600,
        "f1"               : 0.1117,
        "threshold"        : weights["threshold"],
        "xgb_weight"       : weights["xgb_weight"],
        "lgb_weight"       : weights["lgb_weight"],
        "xgb_auc_pr"       : weights["xgb_auc_pr"],
        "lgb_auc_pr"       : weights["lgb_auc_pr"],
        "confusion_matrix" : {
            "tn": 6285636, "fp": 87726,
            "fn": 1294,    "tp": 5599
        },
        "top_features"     : [
            {"name": "payment_format_risk", "importance": 0.4007},
            {"name": "amount_log",          "importance": 0.0870},
            {"name": "fan_out_degree",      "importance": 0.0837},
            {"name": "tx_velocity",         "importance": 0.0753},
            {"name": "amount_per_tx",       "importance": 0.0630},
            {"name": "fan_in_degree",       "importance": 0.0588},
            {"name": "bank_risk_score",     "importance": 0.0516},
            {"name": "amount_zscore_per_bank", "importance": 0.0395},
        ],
        "total_transactions": 6380255,
        "total_flagged"     : 93325,
    }

# ── Unload Qwen manually (free VRAM) ──────────────────────────
@app.post("/qwen/unload")
async def unload_qwen():
    """Manually free Qwen VRAM when not needed."""
    if not xai_service.loaded:
        return {"message": "Qwen is not loaded"}
    xai_service.unload()
    return {"message": "Qwen unloaded — VRAM freed"}

# ── Qwen status ────────────────────────────────────────────────
@app.get("/qwen/status")
async def qwen_status():
    vram = xai_service.get_vram_info()
    return {
        "loaded"    : xai_service.loaded,
        "model_id"  : "Qwen/Qwen2.5-1.5B-Instruct",
        "quantized" : "4-bit NF4",
        "vram"      : vram
    }

# ── Run ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)