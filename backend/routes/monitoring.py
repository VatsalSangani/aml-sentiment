from fastapi import APIRouter

from db import monitor
from services.drift_detector import run_drift_report, get_score_distribution

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/drift")
async def drift(days: int = 7):
    return run_drift_report(days)


@router.get("/recent")
async def recent(limit: int = 10, days: int = 1):
    predictions = monitor.get_recent_predictions(limit=limit, days=days)
    total = len(monitor.get_recent_rows(days))
    return {"predictions": predictions, "total": total}


@router.get("/stats")
async def stats(days: int = 30):
    rows = monitor.get_recent_rows(days)
    if not rows:
        return {"status": "no_data", "n_transactions": 0}

    n        = len(rows)
    scores   = sorted(r[0] for r in rows)
    verdicts = [r[1] for r in rows]
    formats  = [r[2] for r in rows]

    format_breakdown: dict[str, int] = {}
    for fmt in formats:
        format_breakdown[fmt] = format_breakdown.get(fmt, 0) + 1

    return {
        "status"            : "ok",
        "n_transactions"    : n,
        "flag_rate"         : verdicts.count("FLAGGED") / n,
        "avg_score"         : sum(scores) / n,
        "score_p95"         : scores[min(int(n * 0.95), n - 1)],
        "score_p99"         : scores[min(int(n * 0.99), n - 1)],
        "format_breakdown"  : format_breakdown,
        "score_distribution": get_score_distribution(days),
    }


@router.get("/health")
async def monitoring_health():
    total   = monitor.get_total_logged()
    last_7  = len(monitor.get_recent_rows(7))
    last_24 = len(monitor.get_recent_rows(1))
    drift_ready = last_7 >= 20

    return {
        "total_logged"    : total,
        "last_7_days"     : last_7,
        "last_24_hours"   : last_24,
        "drift_ready"     : drift_ready,
        "drift_ready_msg" : (
            None if drift_ready
            else f"Need at least 20 transactions in the last 7 days for drift detection ({last_7} logged so far)."
        ),
    }
