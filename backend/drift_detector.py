"""
AML Sentinel — Drift Detector
Compares live prediction statistics against training baselines.
Detects data drift, concept drift, and prediction drift.

Baselines come from your EDA and training results:
  - PROJECT_NOTES.md    (EDA findings)
  - MODEL_TRAINING_NOTES.md (training stats)
  - feature_importance.csv
"""

import logging
import numpy as np
from monitor import get_recent_rows

logger = logging.getLogger(__name__)

# ── Training baselines ─────────────────────────────────────────
# These are the ground-truth distributions from your 32M row dataset.
# Source: PROJECT_NOTES.md EDA + model evaluation results.

TRAINING_BASELINES = {
    # Prediction distribution
    "flag_rate"              : 0.0146,   # 1.46% flagged at threshold 0.65
    "avg_risk_score"         : 0.312,    # avg score across all test transactions
    "score_p95"              : 0.891,    # 95th percentile score

    # Payment format mix (from EDA payment format analysis)
    "pct_ach"                : 0.180,    # 18% ACH in training data
    "pct_wire"               : 0.220,    # 22% Wire
    "pct_bitcoin"            : 0.035,    # 3.5% Bitcoin
    "pct_cash"               : 0.180,    # 18% Cash

    # Feature distributions
    "avg_payment_format_risk": 1.820,    # weighted avg across formats
    "avg_currency_risk"      : 2.940,    # avg currency risk score
    "pct_cross_border"       : 0.480,    # 48% cross-border
    "pct_near_threshold"     : 0.031,    # 3.1% in $8K-$10K range
    "pct_in_cycle"           : 0.004,    # 0.4% circular (rare but lethal)
    "avg_fan_out"            : 2.210,    # avg unique receivers per account
    "avg_bank_risk"          : 0.089,    # avg bank risk score

    # Performance (concept drift proxies)
    "avg_processing_ms"      : 2800,     # avg inference time
}

# ── Drift thresholds ───────────────────────────────────────────
# How much a metric must change (relative %) before alerting.
# Tighter for high-importance features, looser for stable ones.

DRIFT_THRESHOLDS = {
    # Critical — payment_format_risk is 40% of model importance
    "flag_rate"              : 0.30,   # alert if flag rate changes >30%
    "avg_risk_score"         : 0.20,   # score distribution shifting
    "pct_ach"                : 0.25,   # ACH share changing significantly
    "avg_payment_format_risk": 0.20,   # overall payment risk mix

    # Important
    "pct_cross_border"       : 0.25,
    "pct_bitcoin"            : 0.50,   # loose — Bitcoin is naturally volatile
    "pct_near_threshold"     : 0.40,   # structuring window usage
    "avg_fan_out"            : 0.30,

    # Informational
    "avg_currency_risk"      : 0.25,
    "pct_in_cycle"           : 0.60,   # very rare so high threshold
    "avg_bank_risk"          : 0.30,
    "score_p95"              : 0.15,
}

# ── Severity classification ────────────────────────────────────
def _severity(change_pct: float, threshold: float) -> str:
    ratio = change_pct / threshold
    if ratio >= 2.0:
        return "CRITICAL"
    elif ratio >= 1.5:
        return "HIGH"
    else:
        return "MEDIUM"


# ── What each alert means for the model ───────────────────────
DRIFT_EXPLANATIONS = {
    "flag_rate": (
        "Alert rate has shifted significantly. "
        "If rising: launderers may be using riskier patterns or threshold needs adjustment. "
        "If falling: model may be missing new laundering techniques."
    ),
    "avg_risk_score": (
        "Average risk score distribution has shifted. "
        "Could indicate data distribution change or model miscalibration."
    ),
    "pct_ach": (
        "ACH transaction share has changed. Critical — ACH is your most important feature (40% importance). "
        "If ACH drops heavily, model loses its strongest signal."
    ),
    "avg_payment_format_risk": (
        "Overall payment format risk mix has shifted. "
        "Launderers may be switching to lower-risk payment methods."
    ),
    "pct_cross_border": (
        "Cross-border transaction share changed. "
        "May indicate new transaction routing patterns."
    ),
    "pct_near_threshold": (
        "Structuring pattern frequency changed. "
        "If dropping: launderers may have changed amount strategies. "
        "If rising: potential coordinated structuring campaign."
    ),
    "pct_in_cycle": (
        "Circular transaction frequency changed. "
        "This is your 154x lift signal — any drift here is high priority. "
        "If dropping: launderers may have stopped cycling, model loses key signal."
    ),
    "avg_fan_out": (
        "Account fan-out distribution shifted. "
        "If rising: potential increase in smurfing activity. "
        "If falling: launderers may be using fewer recipient accounts."
    ),
    "pct_bitcoin": (
        "Bitcoin transaction share changed. "
        "Crypto adoption or mixer activity may be increasing."
    ),
}


def run_drift_report(days: int = 7) -> dict:
    """
    Main drift detection function.
    Returns full report with alerts, current stats, and baselines.

    Args:
        days: lookback window in days

    Returns:
        dict with keys: status, alerts, current_stats,
                        baseline_stats, period_days, n_transactions
    """
    rows = get_recent_rows(days)

    if len(rows) < 20:
        return {
            "status"          : "INSUFFICIENT_DATA",
            "message"         : f"Only {len(rows)} transactions in the last {days} days. Need at least 20 for drift analysis.",
            "period_days"     : days,
            "n_transactions"  : len(rows),
            "alerts"          : [],
            "current_stats"   : {},
            "baseline_stats"  : TRAINING_BASELINES,
        }

    # ── Unpack rows ────────────────────────────────────────────
    # row order from monitor.get_recent_rows():
    # 0:risk_score, 1:verdict, 2:payment_format, 3:currency,
    # 4:is_cross_border, 5:is_near_threshold,
    # 6:payment_format_risk, 7:currency_risk_score,
    # 8:bank_risk_score, 9:amount_log, 10:fan_out_degree,
    # 11:tx_velocity, 12:is_in_cycle, 13:amount_usd, 14:processing_ms

    n             = len(rows)
    scores        = [r[0] for r in rows]
    verdicts      = [r[1] for r in rows]
    formats       = [r[2] for r in rows]
    cross_border  = [r[4] for r in rows]
    near_thresh   = [r[5] for r in rows]
    pfr           = [r[6] for r in rows]
    cr            = [r[7] for r in rows]
    bank_risk     = [r[8] for r in rows]
    fan_out       = [r[10] for r in rows]
    in_cycle      = [r[12] for r in rows]
    proc_ms       = [r[14] for r in rows if r[14]]

    sorted_scores = sorted(scores)

    # ── Compute current stats ──────────────────────────────────
    current = {
        "flag_rate"              : verdicts.count("FLAGGED") / n,
        "avg_risk_score"         : round(float(np.mean(scores)), 4),
        "score_p95"              : round(sorted_scores[int(n * 0.95)], 4) if n >= 20 else None,
        "pct_ach"                : formats.count("ACH") / n,
        "pct_wire"               : formats.count("Wire") / n,
        "pct_bitcoin"            : formats.count("Bitcoin") / n,
        "pct_cash"               : formats.count("Cash") / n,
        "avg_payment_format_risk": round(float(np.mean(pfr)), 4),
        "avg_currency_risk"      : round(float(np.mean(cr)), 4),
        "pct_cross_border"       : round(sum(cross_border) / n, 4),
        "pct_near_threshold"     : round(sum(near_thresh) / n, 4),
        "pct_in_cycle"           : round(sum(in_cycle) / n, 4),
        "avg_fan_out"            : round(float(np.mean(fan_out)), 4),
        "avg_bank_risk"          : round(float(np.mean(bank_risk)), 4),
        "avg_processing_ms"      : round(float(np.mean(proc_ms)), 1) if proc_ms else None,
    }

    # ── Detect drift ───────────────────────────────────────────
    alerts = []
    for metric, baseline in TRAINING_BASELINES.items():
        if metric not in current or current[metric] is None:
            continue
        if baseline == 0:
            continue

        threshold  = DRIFT_THRESHOLDS.get(metric, 0.25)
        change_abs = abs(current[metric] - baseline)
        change_pct = change_abs / abs(baseline)

        if change_pct > threshold:
            direction = "↑ HIGHER" if current[metric] > baseline else "↓ LOWER"
            alerts.append({
                "metric"     : metric,
                "baseline"   : baseline,
                "current"    : current[metric],
                "change_pct" : round(change_pct * 100, 1),
                "direction"  : direction,
                "severity"   : _severity(change_pct, threshold),
                "explanation": DRIFT_EXPLANATIONS.get(metric, "Feature distribution has shifted from training baseline."),
                "action"     : _recommend_action(metric, current[metric], baseline),
            })

    # Sort by severity
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    alerts.sort(key=lambda a: sev_order.get(a["severity"], 3))

    # ── Overall status ─────────────────────────────────────────
    if any(a["severity"] == "CRITICAL" for a in alerts):
        status = "CRITICAL_DRIFT"
    elif any(a["severity"] == "HIGH" for a in alerts):
        status = "DRIFT_DETECTED"
    elif alerts:
        status = "MINOR_DRIFT"
    else:
        status = "STABLE"

    return {
        "status"          : status,
        "period_days"     : days,
        "n_transactions"  : n,
        "alerts"          : alerts,
        "current_stats"   : current,
        "baseline_stats"  : TRAINING_BASELINES,
        "recommendation"  : _overall_recommendation(status, alerts),
    }


def _recommend_action(metric: str, current: float, baseline: float) -> str:
    """Per-metric actionable recommendation."""
    going_up = current > baseline
    actions = {
        "flag_rate": (
            "Review recent flagged transactions manually. Consider threshold recalibration."
            if going_up else
            "Investigate whether new laundering patterns are evading detection. Consider retraining."
        ),
        "pct_ach": (
            "ACH volume increased — monitor closely as this is your top feature."
            if going_up else
            "ACH volume dropping — model's strongest signal weakening. Consider retraining if sustained."
        ),
        "pct_in_cycle": (
            "Circular transactions increasing — potential coordinated laundering campaign. Escalate."
            if going_up else
            "Circular patterns dropping. Launderers may have adapted. Retrain if sustained >14 days."
        ),
        "avg_risk_score": (
            "Score inflation detected. Check if threshold needs adjustment upward."
            if going_up else
            "Score deflation detected. Model may be missing new fraud patterns."
        ),
        "pct_near_threshold": (
            "Structuring activity increasing. Consider lowering detection threshold temporarily."
            if going_up else
            "Structuring patterns decreasing. Launderers may have shifted amount ranges."
        ),
    }
    return actions.get(metric, "Monitor for 7 more days. If drift persists, schedule model retraining.")


def _overall_recommendation(status: str, alerts: list) -> str:
    """Top-level recommendation based on overall drift status."""
    if status == "STABLE":
        return "Model is performing within expected parameters. Continue standard monitoring."
    elif status == "MINOR_DRIFT":
        return "Minor distributional shifts detected. No immediate action required. Review in 7 days."
    elif status == "DRIFT_DETECTED":
        critical_metrics = [a["metric"] for a in alerts if a["severity"] == "HIGH"]
        return (
            f"Significant drift detected in: {', '.join(critical_metrics)}. "
            "Schedule model retraining within 30 days. "
            "Increase manual review rate for flagged transactions in the interim."
        )
    elif status == "CRITICAL_DRIFT":
        return (
            "CRITICAL: Model may no longer be reliable. "
            "Immediately increase manual review to 100% of flagged transactions. "
            "Initiate emergency retraining procedure. "
            "Notify compliance team."
        )
    return "Unknown status."


def get_score_distribution(days: int = 30) -> dict:
    """Returns score distribution bucketed into deciles for charting."""
    rows = get_recent_rows(days)
    if not rows:
        return {}

    scores = [r[0] for r in rows]
    buckets = {f"{i*10}-{(i+1)*10}%": 0 for i in range(10)}
    for s in scores:
        bucket_idx = min(int(s * 10), 9)
        key = f"{bucket_idx*10}-{(bucket_idx+1)*10}%"
        buckets[key] += 1

    total = len(scores)
    return {k: {"count": v, "pct": round(v/total*100, 1)} for k, v in buckets.items()}