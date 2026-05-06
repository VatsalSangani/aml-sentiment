"""
AML Sentinel — Drift Detector
Compares live prediction statistics against training baselines.
"""

import logging
from typing import Any

import numpy as np

from db.monitor import get_recent_rows

logger = logging.getLogger(__name__)

TRAINING_BASELINES: dict[str, float] = {
    "flag_rate"              : 0.0146,
    "avg_risk_score"         : 0.312,
    "score_p95"              : 0.891,
    "pct_ach"                : 0.180,
    "pct_wire"               : 0.220,
    "pct_bitcoin"            : 0.035,
    "pct_cash"               : 0.180,
    "avg_payment_format_risk": 1.820,
    "avg_currency_risk"      : 2.940,
    "pct_cross_border"       : 0.480,
    "pct_near_threshold"     : 0.031,
    "pct_in_cycle"           : 0.004,
    "avg_fan_out"            : 2.210,
    "avg_bank_risk"          : 0.089,
    "avg_processing_ms"      : 2800,
}

DRIFT_THRESHOLDS: dict[str, float] = {
    "flag_rate"              : 0.30,
    "avg_risk_score"         : 0.20,
    "pct_ach"                : 0.25,
    "avg_payment_format_risk": 0.20,
    "pct_cross_border"       : 0.25,
    "pct_bitcoin"            : 0.50,
    "pct_near_threshold"     : 0.40,
    "avg_fan_out"            : 0.30,
    "avg_currency_risk"      : 0.25,
    "pct_in_cycle"           : 0.60,
    "avg_bank_risk"          : 0.30,
    "score_p95"              : 0.15,
}

DRIFT_EXPLANATIONS: dict[str, str] = {
    "flag_rate": (
        "Alert rate has shifted significantly. "
        "If rising: launderers may be using riskier patterns or threshold needs adjustment. "
        "If falling: model may be missing new laundering techniques."
    ),
    "avg_risk_score": "Average risk score distribution has shifted. Could indicate data distribution change or model miscalibration.",
    "pct_ach": "ACH transaction share has changed. Critical — ACH is your most important feature (40% importance). If ACH drops heavily, model loses its strongest signal.",
    "avg_payment_format_risk": "Overall payment format risk mix has shifted. Launderers may be switching to lower-risk payment methods.",
    "pct_cross_border": "Cross-border transaction share changed. May indicate new transaction routing patterns.",
    "pct_near_threshold": "Structuring pattern frequency changed. If dropping: launderers may have changed amount strategies. If rising: potential coordinated structuring campaign.",
    "pct_in_cycle": "Circular transaction frequency changed. This is your 154x lift signal — any drift here is high priority.",
    "avg_fan_out": "Account fan-out distribution shifted. If rising: potential increase in smurfing activity.",
    "pct_bitcoin": "Bitcoin transaction share changed. Crypto adoption or mixer activity may be increasing.",
}


def _severity(change_pct: float, threshold: float) -> str:
    ratio = change_pct / threshold
    if ratio >= 2.0:   return "CRITICAL"
    elif ratio >= 1.5: return "HIGH"
    return "MEDIUM"


def run_drift_report(days: int = 7) -> dict[str, Any]:
    rows = get_recent_rows(days)

    if len(rows) < 20:
        return {
            "status"        : "INSUFFICIENT_DATA",
            "message"       : f"Only {len(rows)} transactions in the last {days} days. Need at least 20.",
            "period_days"   : days,
            "n_transactions": len(rows),
            "alerts"        : [],
            "current_stats" : {},
            "baseline_stats": TRAINING_BASELINES,
        }

    n            = len(rows)
    scores       = [r[0] for r in rows]
    verdicts     = [r[1] for r in rows]
    formats      = [r[2] for r in rows]
    cross_border = [r[4] for r in rows]
    near_thresh  = [r[5] for r in rows]
    pfr          = [r[6] for r in rows]
    cr           = [r[7] for r in rows]
    bank_risk    = [r[8] for r in rows]
    fan_out      = [r[10] for r in rows]
    in_cycle     = [r[12] for r in rows]
    proc_ms      = [r[14] for r in rows if r[14]]

    sorted_scores = sorted(scores)
    current: dict[str, Any] = {
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

    alerts = []
    for metric, baseline in TRAINING_BASELINES.items():
        if metric not in current or current[metric] is None or baseline == 0:
            continue
        threshold  = DRIFT_THRESHOLDS.get(metric, 0.25)
        change_pct = abs(current[metric] - baseline) / abs(baseline)
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

    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    alerts.sort(key=lambda a: sev_order.get(a["severity"], 3))

    if any(a["severity"] == "CRITICAL" for a in alerts):   status = "CRITICAL_DRIFT"
    elif any(a["severity"] == "HIGH" for a in alerts):     status = "DRIFT_DETECTED"
    elif alerts:                                            status = "MINOR_DRIFT"
    else:                                                   status = "STABLE"

    return {
        "status"        : status,
        "period_days"   : days,
        "n_transactions": n,
        "alerts"        : alerts,
        "current_stats" : current,
        "baseline_stats": TRAINING_BASELINES,
        "recommendation": _overall_recommendation(status, alerts),
    }


def _recommend_action(metric: str, current: float, baseline: float) -> str:
    going_up = current > baseline
    actions = {
        "flag_rate"        : "Review recent flagged transactions manually. Consider threshold recalibration." if going_up else "Investigate whether new laundering patterns are evading detection. Consider retraining.",
        "pct_ach"          : "ACH volume increased — monitor closely as this is your top feature." if going_up else "ACH volume dropping — model's strongest signal weakening. Consider retraining if sustained.",
        "pct_in_cycle"     : "Circular transactions increasing — potential coordinated laundering campaign. Escalate." if going_up else "Circular patterns dropping. Launderers may have adapted. Retrain if sustained >14 days.",
        "avg_risk_score"   : "Score inflation detected. Check if threshold needs adjustment upward." if going_up else "Score deflation detected. Model may be missing new fraud patterns.",
        "pct_near_threshold": "Structuring activity increasing. Consider lowering detection threshold temporarily." if going_up else "Structuring patterns decreasing. Launderers may have shifted amount ranges.",
    }
    return actions.get(metric, "Monitor for 7 more days. If drift persists, schedule model retraining.")


def _overall_recommendation(status: str, alerts: list) -> str:
    if status == "STABLE":
        return "Model is performing within expected parameters. Continue standard monitoring."
    elif status == "MINOR_DRIFT":
        return "Minor distributional shifts detected. No immediate action required. Review in 7 days."
    elif status == "DRIFT_DETECTED":
        metrics = [a["metric"] for a in alerts if a["severity"] == "HIGH"]
        return f"Significant drift detected in: {', '.join(metrics)}. Schedule model retraining within 30 days. Increase manual review rate for flagged transactions."
    elif status == "CRITICAL_DRIFT":
        return "CRITICAL: Model may no longer be reliable. Immediately increase manual review to 100% of flagged transactions. Initiate emergency retraining procedure. Notify compliance team."
    return "Unknown status."


def get_score_distribution(days: int = 30) -> dict:
    rows = get_recent_rows(days)
    if not rows:
        return {}
    scores  = [r[0] for r in rows]
    buckets = {f"{i*10}-{(i+1)*10}%": 0 for i in range(10)}
    for s in scores:
        key = f"{min(int(s * 10), 9) * 10}-{min(int(s * 10), 9) * 10 + 10}%"
        buckets[key] += 1
    total = len(scores)
    return {k: {"count": v, "pct": round(v / total * 100, 1)} for k, v in buckets.items()}
