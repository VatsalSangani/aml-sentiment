import json
import os

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/stats")
async def get_stats():
    """Return model evaluation stats from saved ensemble weights."""
    from config import (
        MODELS_DIR,
        MODEL_AUC_ROC, MODEL_AUC_PR, MODEL_RECALL, MODEL_PRECISION,
        MODEL_F1, MODEL_TOTAL_TRANS, MODEL_TOTAL_FLAGGED,
        MODEL_CONFUSION_MATRIX, MODEL_TOP_FEATURES,
    )

    weights_path = os.path.join(MODELS_DIR, "ensemble_weights.json")
    if not os.path.exists(weights_path):
        raise HTTPException(status_code=404, detail="ensemble_weights.json not found.")

    with open(weights_path, "r") as f:
        weights = json.load(f)

    return {
        "auc_roc"           : MODEL_AUC_ROC,
        "auc_pr"            : MODEL_AUC_PR,
        "recall"            : MODEL_RECALL,
        "precision"         : MODEL_PRECISION,
        "f1"                : MODEL_F1,
        "threshold"         : weights["threshold"],
        "xgb_weight"        : weights["xgb_weight"],
        "lgb_weight"        : weights["lgb_weight"],
        "xgb_auc_pr"        : weights["xgb_auc_pr"],
        "lgb_auc_pr"        : weights["lgb_auc_pr"],
        "confusion_matrix"  : MODEL_CONFUSION_MATRIX,
        "top_features"      : MODEL_TOP_FEATURES,
        "total_transactions": MODEL_TOTAL_TRANS,
        "total_flagged"     : MODEL_TOTAL_FLAGGED,
    }
