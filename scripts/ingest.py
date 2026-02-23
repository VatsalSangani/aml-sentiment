# ╔══════════════════════════════════════════════════════════════╗
# ║          AML Sentinel — Data Ingestion                      ║
# ║          Native Windows Version                             ║
# ╚══════════════════════════════════════════════════════════════╝

import sys
import os

# ── Config ─────────────────────────────────────────────────────
sys.path.append(r"C:\Users\VatsaL\Desktop\Datasets\AML_Sentinel")
from config import *

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp
from pyspark.sql.types import (
    StructType, StructField, StringType,
    DoubleType, IntegerType
)

# ── Spark Session ──────────────────────────────────────────────
spark = SparkSession.builder \
    .appName("AML_Ingestion") \
    .config("spark.driver.memory", SPARK_DRIVER_MEMORY) \
    .config("spark.sql.shuffle.partitions", SPARK_SHUFFLE_PARTITIONS) \
    .config("spark.pyspark.python", PYSPARK_PYTHON) \
    .config("spark.pyspark.driver.python", PYSPARK_PYTHON) \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# ── Define Schemas ─────────────────────────────────────────────
trans_schema = StructType([
    StructField("Timestamp",          StringType(),  True),
    StructField("From Bank",          StringType(),  True),
    StructField("Account",            StringType(),  True),
    StructField("To Bank",            StringType(),  True),
    StructField("Account.1",          StringType(),  True),
    StructField("Amount Received",    DoubleType(),  True),
    StructField("Receiving Currency", StringType(),  True),
    StructField("Amount Paid",        DoubleType(),  True),
    StructField("Payment Currency",   StringType(),  True),
    StructField("Payment Format",     StringType(),  True),
    StructField("Is Laundering",      IntegerType(), True),
])

accounts_schema = StructType([
    StructField("Bank",    StringType(), True),
    StructField("Account", StringType(), True),
    StructField("Name",    StringType(), True),
    StructField("Street",  StringType(), True),
    StructField("City",    StringType(), True),
    StructField("State",   StringType(), True),
    StructField("Country", StringType(), True),
    StructField("Zip",     StringType(), True),
])

# ── Load CSVs ──────────────────────────────────────────────────
print("📥 Loading Transactions CSV...")
print(f"   Path: {TRANS_CSV}")
trans_df = spark.read.csv(
    TRANS_CSV,
    header=True,
    schema=trans_schema
)

print("📥 Loading Accounts CSV...")
print(f"   Path: {ACCOUNTS_CSV}")
accounts_df = spark.read.csv(
    ACCOUNTS_CSV,
    header=True,
    schema=accounts_schema
)

# ── Basic Cleaning ─────────────────────────────────────────────
print("\n🧹 Cleaning data...")
trans_df = trans_df.dropna(
    subset=["Timestamp", "From Bank", "To Bank", "Amount Paid"]
)

# Convert Timestamp to proper type
trans_df = trans_df.withColumn(
    "Timestamp",
    to_timestamp(col("Timestamp"), "yyyy/MM/dd HH:mm")
)

# ── Basic Stats ────────────────────────────────────────────────
total      = trans_df.count()
laundering = trans_df.filter(col("Is Laundering") == 1).count()
legit      = total - laundering

print("\n" + "=" * 55)
print("📊 DATASET SUMMARY")
print("=" * 55)
print(f"Total Transactions  : {total:,}")
print(f"Legitimate          : {legit:,} ({legit/total*100:.3f}%)")
print(f"Money Laundering    : {laundering:,} ({laundering/total*100:.3f}%)")
print("=" * 55)

print("\n📋 Transaction Schema:")
trans_df.printSchema()

print("\n👀 Sample Transactions:")
trans_df.show(5, truncate=False)

print("\n📋 Accounts Schema:")
accounts_df.printSchema()

print("\n👀 Sample Accounts:")
accounts_df.show(5, truncate=False)

# ── Save as Parquet ────────────────────────────────────────────
print("\n💾 Saving as Parquet for faster future reads...")
print(f"   Saving transactions to : {TRANS_PARQUET}")
trans_df.write.mode("overwrite").parquet(TRANS_PARQUET)

print(f"   Saving accounts to     : {ACCOUNTS_PARQUET}")
accounts_df.write.mode("overwrite").parquet(ACCOUNTS_PARQUET)

print("\n" + "=" * 55)
print("✅ Ingestion Complete!")
print(f"   trans_medium.parquet    saved ✅")
print(f"   accounts_medium.parquet saved ✅")
print("=" * 55)

spark.stop()