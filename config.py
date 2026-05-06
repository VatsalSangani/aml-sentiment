# AML Sentinel — Path & Spark Configuration
# Import this in every notebook/script

import os

# ── Base Project Directory ─────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Data Directories ───────────────────────────────────────────
DATA_DIR      = os.path.join(BASE_DIR, "data")
MODELS_DIR    = os.path.join(BASE_DIR, "models")
EDA_DIR       = os.path.join(BASE_DIR, "eda_outputs")
TRAINING_DIR  = os.path.join(BASE_DIR, "training_outputs")
SCRIPTS_DIR   = os.path.join(BASE_DIR, "scripts")
NOTEBOOKS_DIR = os.path.join(BASE_DIR, "notebooks")

# ── Raw Data Files ─────────────────────────────────────────────
TRANS_CSV    = os.path.join(DATA_DIR, "HI-Medium_Trans.csv")
ACCOUNTS_CSV = os.path.join(DATA_DIR, "HI-Medium_accounts.csv")
PATTERNS_TXT = os.path.join(DATA_DIR, "HI-Medium_Patterns.txt")

# ── Parquet Files ──────────────────────────────────────────────
TRANS_PARQUET          = os.path.join(DATA_DIR, "trans_medium.parquet")
ACCOUNTS_PARQUET       = os.path.join(DATA_DIR, "accounts_medium.parquet")
FEATURES_1_PARQUET     = os.path.join(DATA_DIR, "features_1.parquet")
FEATURES_2_PARQUET     = os.path.join(DATA_DIR, "features_2.parquet")
FEATURES_FINAL_PARQUET = os.path.join(DATA_DIR, "features_final.parquet")

# ── Model Files ────────────────────────────────────────────────
XGB_MODEL      = os.path.join(MODELS_DIR, "xgb_model.json")
LGB_MODEL      = os.path.join(MODELS_DIR, "lgb_model.txt")
THRESHOLD_FILE = os.path.join(MODELS_DIR, "threshold.txt")
FEAT_IMP_FILE  = os.path.join(MODELS_DIR, "feature_importance.csv")

# ── EDA Output Files ───────────────────────────────────────────
EDA_REPORT = os.path.join(EDA_DIR, "eda_report.png")
GRAPH_EDA  = os.path.join(EDA_DIR, "graph_eda_report.png")

# ── Spark Config ───────────────────────────────────────────────
SPARK_DRIVER_MEMORY      = "2g"
SPARK_SHUFFLE_PARTITIONS = "8"

# ── API / Backend ──────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8503

# ── Model Performance Metrics (from training evaluation) ───────
MODEL_AUC_ROC          = 0.9857
MODEL_AUC_PR           = 0.3857
MODEL_RECALL           = 0.8123
MODEL_PRECISION        = 0.0600
MODEL_F1               = 0.1117
MODEL_TOTAL_TRANS      = 6_380_255
MODEL_TOTAL_FLAGGED    = 93_325
MODEL_CONFUSION_MATRIX = {"tn": 6_285_636, "fp": 87_726, "fn": 1_294, "tp": 5_599}
MODEL_TOP_FEATURES = [
    {"name": "payment_format_risk",    "importance": 0.4007},
    {"name": "amount_log",             "importance": 0.0870},
    {"name": "fan_out_degree",         "importance": 0.0837},
    {"name": "tx_velocity",            "importance": 0.0753},
    {"name": "amount_per_tx",          "importance": 0.0630},
    {"name": "fan_in_degree",          "importance": 0.0588},
    {"name": "bank_risk_score",        "importance": 0.0516},
    {"name": "amount_zscore_per_bank", "importance": 0.0395},
]

# ── Create Directories ─────────────────────────────────────────
for _dir in [DATA_DIR, MODELS_DIR, EDA_DIR, TRAINING_DIR, SCRIPTS_DIR, NOTEBOOKS_DIR]:
    os.makedirs(_dir, exist_ok=True)


def get_spark_session(app_name: str = "AML_Sentinel"):
    """Create and return a Spark session configured for Linux/EC2."""
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .appName(app_name)
        .config("spark.driver.memory",          SPARK_DRIVER_MEMORY)
        .config("spark.sql.shuffle.partitions", SPARK_SHUFFLE_PARTITIONS)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


if __name__ == "__main__":
    print("=" * 55)
    print("📁 AML SENTINEL — PATH CONFIG")
    print("=" * 55)
    print(f"  Base Dir   : {BASE_DIR}")
    print(f"  Data Dir   : {DATA_DIR}")
    print(f"  Models Dir : {MODELS_DIR}")
    print(f"  API Port   : {API_PORT}")
    print(f"  Spark Mem  : {SPARK_DRIVER_MEMORY}")
    print(f"\n📄 Raw Files:")
    print(f"  Trans CSV  : {os.path.exists(TRANS_CSV)} → {TRANS_CSV}")
    print("=" * 55)
