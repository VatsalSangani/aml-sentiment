# ╔══════════════════════════════════════════════════════════════╗
# ║          AML Sentinel — Path Configuration                  ║
# ║          Import this in every notebook/script               ║
# ╚══════════════════════════════════════════════════════════════╝

import os

# ── Base Project Directory ─────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Data Directories ───────────────────────────────────────────
DATA_DIR        = os.path.join(BASE_DIR, "data")
MODELS_DIR      = os.path.join(BASE_DIR, "models")
EDA_DIR         = os.path.join(BASE_DIR, "eda_outputs")
TRAINING_DIR    = os.path.join(BASE_DIR, "training_outputs")
SCRIPTS_DIR     = os.path.join(BASE_DIR, "scripts")
NOTEBOOKS_DIR   = os.path.join(BASE_DIR, "notebooks")

# ── Raw Data Files ─────────────────────────────────────────────
TRANS_CSV       = os.path.join(DATA_DIR, "HI-Medium_Trans.csv")
ACCOUNTS_CSV    = os.path.join(DATA_DIR, "HI-Medium_accounts.csv")
PATTERNS_TXT    = os.path.join(DATA_DIR, "HI-Medium_Patterns.txt")

# ── Parquet Files ──────────────────────────────────────────────
TRANS_PARQUET           = os.path.join(DATA_DIR, "trans_medium.parquet")
ACCOUNTS_PARQUET        = os.path.join(DATA_DIR, "accounts_medium.parquet")
FEATURES_1_PARQUET      = os.path.join(DATA_DIR, "features_1.parquet")
FEATURES_2_PARQUET      = os.path.join(DATA_DIR, "features_2.parquet")
FEATURES_FINAL_PARQUET  = os.path.join(DATA_DIR, "features_final.parquet")

# ── Model Files ────────────────────────────────────────────────
XGB_MODEL       = os.path.join(MODELS_DIR, "xgb_model.json")
LGB_MODEL       = os.path.join(MODELS_DIR, "lgb_model.txt")
THRESHOLD_FILE  = os.path.join(MODELS_DIR, "threshold.txt")
FEAT_IMP_FILE   = os.path.join(MODELS_DIR, "feature_importance.csv")

# ── EDA Output Files ───────────────────────────────────────────
EDA_REPORT      = os.path.join(EDA_DIR, "eda_report.png")
GRAPH_EDA       = os.path.join(EDA_DIR, "graph_eda_report.png")

# ── Paths ──────────────────────────────────────────────────────
PYSPARK_PYTHON   = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
HADOOP_HOME_PATH = "C:\\hadoop"

# ── Create Directories ─────────────────────────────────────────
for directory in [DATA_DIR, MODELS_DIR, EDA_DIR, TRAINING_DIR,
                  SCRIPTS_DIR, NOTEBOOKS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ── Spark Config ───────────────────────────────────────────────
SPARK_DRIVER_MEMORY      = "6g"
SPARK_SHUFFLE_PARTITIONS = "8"

# ── get_spark_session() — use this in every notebook/script ────
def get_spark_session(app_name="AML_Sentinel"):
    """
    Creates and returns a Spark session with all Windows fixes applied.
    Always use this instead of SparkSession.builder directly.
    """
    # Set env vars BEFORE Spark/JVM starts
    os.environ["HADOOP_HOME"]           = HADOOP_HOME_PATH
    os.environ["PATH"]                  = os.environ["PATH"] + f";{HADOOP_HOME_PATH}\\bin"
    os.environ["PYSPARK_PYTHON"]        = PYSPARK_PYTHON
    os.environ["PYSPARK_DRIVER_PYTHON"] = PYSPARK_PYTHON

    from pyspark.sql import SparkSession

    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.driver.memory",            SPARK_DRIVER_MEMORY) \
        .config("spark.sql.shuffle.partitions",   SPARK_SHUFFLE_PARTITIONS) \
        .config("spark.pyspark.python",           PYSPARK_PYTHON) \
        .config("spark.pyspark.driver.python",    PYSPARK_PYTHON) \
        .config("spark.hadoop.fs.file.impl",
                "org.apache.hadoop.fs.LocalFileSystem") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")
    return spark

# ── Print Config ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("📁 AML SENTINEL — PATH CONFIG")
    print("=" * 55)
    print(f"  Base Dir      : {BASE_DIR}")
    print(f"  Data Dir      : {DATA_DIR}")
    print(f"  Models Dir    : {MODELS_DIR}")
    print(f"  EDA Dir       : {EDA_DIR}")
    print(f"  Hadoop Home   : {HADOOP_HOME_PATH}")
    print(f"  PySpark Python: {PYSPARK_PYTHON}")
    print(f"\n📄 Raw Files:")
    print(f"  Trans CSV     : {os.path.exists(TRANS_CSV)} → {TRANS_CSV}")
    print(f"  Accounts CSV  : {os.path.exists(ACCOUNTS_CSV)} → {ACCOUNTS_CSV}")
    print(f"\n📦 Parquet Files:")
    print(f"  Trans         : {os.path.exists(TRANS_PARQUET)}")
    print(f"  Features Final: {os.path.exists(FEATURES_FINAL_PARQUET)}")
    print("=" * 55)