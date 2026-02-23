# ╔══════════════════════════════════════════════════════════════╗
# ║          AML Sentinel — Environment Check                   ║
# ║          Run: python hardware_check.py                      ║
# ╚══════════════════════════════════════════════════════════════╝

import sys

# ── Unsloth MUST be imported first before all AI libraries ─────
try:
    import unsloth
    UNSLOTH_OK = True
except Exception as e:
    UNSLOTH_OK = False
    UNSLOTH_ERR = str(e)

print("=" * 55)
print("🔍 AML SENTINEL — ENVIRONMENT CHECK")
print("=" * 55)

# ── Python ─────────────────────────────────────────────────────
print(f"\n🐍 Python Version : {sys.version}")

# ── PyTorch + GPU ──────────────────────────────────────────────
print("\n── GPU / PyTorch ──────────────────────────────────────")
try:
    import torch
    print(f"  ✅ PyTorch        : {torch.__version__}")
    if torch.cuda.is_available():
        print(f"  ✅ CUDA Available  : True")
        print(f"  ✅ CUDA Version    : {torch.version.cuda}")
        print(f"  ✅ GPU             : {torch.cuda.get_device_name(0)}")
        print(f"  ✅ VRAM            : {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("  ❌ CUDA Not Available — Check NVIDIA drivers")
except ImportError:
    print("  ❌ PyTorch not installed")

# ── PySpark + Java ─────────────────────────────────────────────
print("\n── PySpark / Java ─────────────────────────────────────")
try:
    from pyspark.sql import SparkSession
    spark = SparkSession.builder \
        .appName("AML_EnvCheck") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    print(f"  ✅ PySpark         : {spark.version}")
    spark.stop()
except Exception as e:
    print(f"  ❌ PySpark Error   : {e}")

# ── ML Stack ───────────────────────────────────────────────────
print("\n── ML / Detection Stack ───────────────────────────────")
try:
    import xgboost as xgb
    print(f"  ✅ XGBoost         : {xgb.__version__}")
except ImportError:
    print("  ❌ XGBoost not installed")

try:
    import lightgbm as lgb
    print(f"  ✅ LightGBM        : {lgb.__version__}")
except ImportError:
    print("  ❌ LightGBM not installed")

try:
    import sklearn
    print(f"  ✅ Scikit-learn    : {sklearn.__version__}")
except ImportError:
    print("  ❌ Scikit-learn not installed")

# ── Data Science ───────────────────────────────────────────────
print("\n── Data Science Stack ─────────────────────────────────")
try:
    import pandas as pd
    print(f"  ✅ Pandas          : {pd.__version__}")
except ImportError:
    print("  ❌ Pandas not installed")

try:
    import numpy as np
    print(f"  ✅ NumPy           : {np.__version__}")
except ImportError:
    print("  ❌ NumPy not installed")

try:
    import pyarrow as pa
    print(f"  ✅ PyArrow         : {pa.__version__}")
except ImportError:
    print("  ❌ PyArrow not installed")

try:
    import matplotlib
    print(f"  ✅ Matplotlib      : {matplotlib.__version__}")
except ImportError:
    print("  ❌ Matplotlib not installed")

try:
    import seaborn as sns
    print(f"  ✅ Seaborn         : {sns.__version__}")
except ImportError:
    print("  ❌ Seaborn not installed")

# ── AI / LLM Stack ─────────────────────────────────────────────
print("\n── AI / LLM Stack ─────────────────────────────────────")

if UNSLOTH_OK:
    print(f"  ✅ Unsloth         : installed")
else:
    print(f"  ❌ Unsloth         : {UNSLOTH_ERR}")

try:
    import transformers
    print(f"  ✅ Transformers    : {transformers.__version__}")
except ImportError:
    print("  ❌ Transformers not installed")

try:
    import peft
    print(f"  ✅ PEFT            : {peft.__version__}")
except ImportError:
    print("  ❌ PEFT not installed")

try:
    import trl
    print(f"  ✅ TRL             : {trl.__version__}")
except ImportError:
    print("  ❌ TRL not installed")

try:
    import accelerate
    print(f"  ✅ Accelerate      : {accelerate.__version__}")
except ImportError:
    print("  ❌ Accelerate not installed")

try:
    import bitsandbytes as bnb
    print(f"  ✅ BitsAndBytes    : {bnb.__version__}")
except ImportError:
    print("  ❌ BitsAndBytes not installed")

# ── Java ───────────────────────────────────────────────────────
print("\n── Java ───────────────────────────────────────────────")
import os
import subprocess
try:
    result = subprocess.run(["java", "-version"], capture_output=True, text=True)
    java_version = result.stderr.strip().split("\n")[0]
    print(f"  ✅ Java            : {java_version}")
    java_home = os.environ.get("JAVA_HOME", "Not Set")
    print(f"  ✅ JAVA_HOME       : {java_home}")
except Exception as e:
    print(f"  ❌ Java Error      : {e}")

print("\n" + "=" * 55)
print("✅ Environment Check Complete!")
print("=" * 55)