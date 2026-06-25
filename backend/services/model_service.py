import json
import math
import os
import sys
import time
from typing import Any

import numpy as np
import shap
import xgboost as xgb
import lightgbm as lgb

# Add project root so config is importable when this module runs standalone
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
from config import MODELS_DIR, XGB_MODEL, LGB_MODEL

PAYMENT_RISK: dict[str, int] = {
    "ACH": 3, "Bitcoin": 2, "Cash": 1, "Cheque": 1,
    "Credit Card": 1, "Wire": 0, "Reinvestment": 0,
}

CURRENCY_RISK: dict[str, int] = {
    "UK Pound": 5, "Ruble": 5, "Euro": 4, "Yen": 4,
    "US Dollar": 3, "Yuan": 3, "Rupee": 3,
    "Australian Dollar": 2, "Canadian Dollar": 2, "Bitcoin": 1,
}

FEATURE_COLS: list[str] = [
    "payment_format_risk", "amount_log", "fan_out_degree",
    "tx_velocity", "amount_per_tx", "fan_in_degree",
    "bank_risk_score", "amount_zscore_per_bank", "hour_of_day",
    "day_of_week", "is_cross_border", "currency_risk_score",
    "is_in_cycle", "is_weekend", "is_peak_hour",
    "is_hub_bank", "is_high_fan_out", "is_near_threshold",
]


class ModelService:
    def __init__(self) -> None:
        self.xgb_model: Any    = None
        self.lgb_booster: Any  = None
        self.explainer: Any    = None
        self.weights_meta: Any = None
        self.loaded: bool      = False

    def load(self) -> None:
        """Load XGBoost, LightGBM and ensemble weights."""
        with open(os.path.join(MODELS_DIR, "ensemble_weights.json"), "r") as f:
            self.weights_meta = json.load(f)

        print("📦 Loading XGBoost...")
        self.xgb_model = xgb.XGBClassifier()
        self.xgb_model.load_model(XGB_MODEL)

        print("📦 Loading LightGBM...")
        self.lgb_booster = lgb.Booster(model_file=LGB_MODEL)

        print("📦 Building SHAP explainer...")
        self.explainer = shap.TreeExplainer(self.xgb_model)

        self.loaded = True
        print("✅ ML models loaded!")

    def build_features(self, req: Any) -> dict[str, Any]:
        """Engineer 18 features from raw transaction input."""
        pfr      = PAYMENT_RISK.get(req.payment_format, 1)
        cr       = CURRENCY_RISK.get(req.currency, 2)
        amt_log  = math.log1p(req.amount)
        is_cross = 1 if req.from_bank != req.to_bank else 0
        is_near  = 1 if 8000 <= req.amount < 10000 else 0
        fan_out  = req.fan_out
        vel      = req.tx_velocity
        amt_per_tx    = req.amount / max(vel, 1)
        hour_of_day   = req.hour_of_day if getattr(req, "hour_of_day", None) is not None else 12
        is_in_cycle   = int(req.is_in_cycle) if getattr(req, "is_in_cycle", None) is not None else 0
        fan_in_degree = req.fan_in if getattr(req, "fan_in", None) is not None else 1
        is_peak_hour  = 1 if 9 <= hour_of_day <= 17 else 0
        is_high_fan   = 1 if fan_out > 50 else 0

        return {
            "payment_format_risk"   : pfr,
            "amount_log"            : round(amt_log, 4),
            "fan_out_degree"        : fan_out,
            "tx_velocity"           : vel,
            "amount_per_tx"         : round(amt_per_tx, 2),
            "fan_in_degree"         : fan_in_degree,
            "bank_risk_score"       : 0.15,
            "amount_zscore_per_bank": 0.0,
            "hour_of_day"           : hour_of_day,
            "day_of_week"           : 2,
            "is_cross_border"       : is_cross,
            "currency_risk_score"   : cr,
            "is_in_cycle"           : is_in_cycle,
            "is_weekend"            : 0,
            "is_peak_hour"          : is_peak_hour,
            "is_hub_bank"           : 0,
            "is_high_fan_out"       : is_high_fan,
            "is_near_threshold"     : is_near,
        }

    def predict(self, req: Any) -> dict[str, Any]:
        """Run full prediction pipeline for one transaction."""
        if not self.loaded:
            self.load()

        t_start  = time.time()
        features = self.build_features(req)
        X = np.array([[features[f] for f in FEATURE_COLS]], dtype=np.float32)

        xgb_w  = self.weights_meta["xgb_weight"]
        lgb_w  = self.weights_meta["lgb_weight"]
        # Decision threshold (0.8514) tuned on the validation-set precision-recall
        # curve to maximise F1. See docs/THRESHOLD_DERIVATION.md for full rationale,
        # validation-vs-test behaviour, and how to re-derive for other objectives.
        thresh = self.weights_meta["threshold"]

        xgb_p  = float(self.xgb_model.predict_proba(X)[0, 1])
        lgb_p  = float(self.lgb_booster.predict(X)[0])
        score  = xgb_w * xgb_p + lgb_w * lgb_p

        shap_vals = self.explainer.shap_values(X)[0]
        drivers   = [
            {
                "feature"  : feat,
                "shap_val" : round(float(val), 4),
                "direction": "increases" if val > 0 else "decreases",
            }
            for feat, val in sorted(
                zip(FEATURE_COLS, shap_vals), key=lambda x: abs(x[1]), reverse=True
            )[:5]
        ]

        return {
            "risk_score"   : round(score, 4),
            "verdict"      : "FLAGGED" if score >= thresh else "CLEARED",
            "threshold"    : thresh,
            "shap_drivers" : drivers,
            "features"     : features,
            "processing_ms": int((time.time() - t_start) * 1000),
        }


model_service = ModelService()
