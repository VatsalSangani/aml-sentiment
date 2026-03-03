"""
AML Sentinel — Prediction Logger
Logs every /analyze call to SQLite for drift monitoring.
On HF Spaces free tier, DB persists until Space restarts.
For persistence across restarts, set PERSIST_TO_HF=True
and configure HF_TOKEN + HF_DATASET_REPO env vars.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Storage path ───────────────────────────────────────────────
# HF Spaces: /data is persistent if enabled, otherwise /tmp
_base = Path(os.environ.get("MONITOR_DB_DIR", "/tmp/aml_monitoring"))
_base.mkdir(parents=True, exist_ok=True)
DB_PATH = _base / "predictions.db"


# ── Schema ─────────────────────────────────────────────────────
_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS predictions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             TEXT    NOT NULL,
    -- raw inputs
    payment_format        TEXT,
    currency              TEXT,
    amount_usd            REAL,
    from_bank             TEXT,
    to_bank               TEXT,
    fan_out               INTEGER,
    tx_velocity           INTEGER,
    -- engineered features (from model_service)
    payment_format_risk   REAL,
    currency_risk_score   REAL,
    is_cross_border       INTEGER,
    is_near_threshold     INTEGER,
    amount_log            REAL,
    bank_risk_score       REAL,
    is_in_cycle           INTEGER,
    fan_out_degree        REAL,
    tx_velocity_feat      REAL,
    -- model output
    risk_score            REAL    NOT NULL,
    verdict               TEXT    NOT NULL,
    processing_ms         INTEGER
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON predictions(timestamp);
CREATE INDEX IF NOT EXISTS idx_verdict   ON predictions(verdict);
"""


def init_db():
    """Create tables if they don't exist. Safe to call multiple times."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(_CREATE_SQL)
        conn.commit()
        conn.close()
        logger.info(f"Monitor DB ready at {DB_PATH}")
    except Exception as e:
        logger.error(f"Monitor DB init failed: {e}")


def log_prediction(request, result: dict, processing_ms: int = 0):
    """
    Log one prediction. Call this inside /analyze after model_service.predict().

    Args:
        request     : TransactionRequest pydantic object
        result      : dict returned by model_service.predict()
        processing_ms: total latency for this request
    """
    try:
        f = result.get("features", {})
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO predictions (
                timestamp, payment_format, currency, amount_usd,
                from_bank, to_bank, fan_out, tx_velocity,
                payment_format_risk, currency_risk_score,
                is_cross_border, is_near_threshold, amount_log,
                bank_risk_score, is_in_cycle, fan_out_degree,
                tx_velocity_feat, risk_score, verdict, processing_ms
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.utcnow().isoformat(),
            request.payment_format,
            request.currency,
            request.amount,
            request.from_bank,
            request.to_bank,
            request.fan_out,
            request.tx_velocity,
            # engineered features
            f.get("payment_format_risk",  0),
            f.get("currency_risk_score",  0),
            int(f.get("is_cross_border",  0)),
            int(f.get("is_near_threshold",0)),
            f.get("amount_log",           0),
            f.get("bank_risk_score",      0),
            int(f.get("is_in_cycle",      0)),
            f.get("fan_out_degree",       request.fan_out),
            f.get("tx_velocity",          request.tx_velocity),
            result["risk_score"],
            result["verdict"],
            processing_ms,
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        # Never let monitoring crash the main prediction pipeline
        logger.warning(f"Failed to log prediction: {e}")


def get_total_logged() -> int:
    """Quick count of all logged predictions."""
    try:
        conn = sqlite3.connect(DB_PATH)
        n = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


def get_recent_rows(days: int = 7) -> list:
    """Return raw rows for the last N days."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT
                risk_score, verdict, payment_format, currency,
                is_cross_border, is_near_threshold,
                payment_format_risk, currency_risk_score,
                bank_risk_score, amount_log, fan_out_degree,
                tx_velocity_feat, is_in_cycle, amount_usd,
                processing_ms
            FROM predictions
            WHERE timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
        """, (f"-{days} days",)).fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to fetch rows: {e}")
        return []


def export_to_json(days: int = 30) -> list:
    """Export recent predictions as list of dicts (for API response)."""
    rows = get_recent_rows(days)
    keys = [
        "risk_score", "verdict", "payment_format", "currency",
        "is_cross_border", "is_near_threshold",
        "payment_format_risk", "currency_risk_score",
        "bank_risk_score", "amount_log", "fan_out_degree",
        "tx_velocity", "is_in_cycle", "amount_usd", "processing_ms"
    ]
    return [dict(zip(keys, r)) for r in rows]