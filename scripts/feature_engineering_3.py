from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, round as spark_round, count, sum, desc, lit
)
import os

py_round = round  # save Python's built-in round before PySpark overwrites

# ── Spark Session ──────────────────────────────────────────────
spark = SparkSession.builder \
    .appName("AML_Features_3_Graph") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "8") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# ── Load from Feature Group 2 output ──────────────────────────
print("📥 Loading features_2 parquet...")
trans_df = spark.read.parquet("/workspace/data/features_2.parquet")
print(f"✅ Loaded {trans_df.count():,} transactions\n")

# ══════════════════════════════════════════════════════════════
# FEATURE 17: is_in_cycle
# From EDA: Circular transactions have 17.267% laundering rate
# = 154x higher than overall rate
# A transaction is in a cycle if A→B AND B→A both exist
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 17: is_in_cycle (most important feature!)")
print("    This may take a few minutes on 32M rows...")

# Build edge set: all (src, dst) pairs that exist
forward_edges = trans_df.select(
    col("Account").alias("src"),
    col("To Account").alias("dst")
).distinct()

# Reverse lookup: does (dst, src) also exist?
reverse_edges = trans_df.select(
    col("Account").alias("dst"),
    col("To Account").alias("src")
).distinct()

# Inner join finds pairs where both directions exist
cycle_pairs = forward_edges.join(reverse_edges, on=["src", "dst"]) \
    .withColumn("cycle_flag", lit(1))

# Join back to transactions
trans_df = trans_df.join(
    cycle_pairs.select(
        col("src").alias("Account"),
        col("dst").alias("To Account"),
        col("cycle_flag")
    ),
    on=["Account", "To Account"],
    how="left"
)

trans_df = trans_df.withColumn(
    "is_in_cycle",
    when(col("cycle_flag") == 1, 1).otherwise(0)
).drop("cycle_flag")

print("    ✅ is_in_cycle computed")

# ══════════════════════════════════════════════════════════════
# FEATURE 18: is_hub_bank
# From EDA: Bank 0272142 self-cycled $3.88B
# Flag known high-risk hub banks
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 18: is_hub_bank")

# Compute hub banks dynamically — top banks by laundering count
hub_banks = trans_df.filter(col("Is Laundering") == 1) \
    .groupBy("From Bank") \
    .count() \
    .orderBy(desc("count")) \
    .limit(20) \
    .select("From Bank") \
    .rdd.flatMap(lambda x: x).collect()

print(f"    Hub banks identified: {hub_banks}")

trans_df = trans_df.withColumn(
    "is_hub_bank",
    when(col("From Bank").isin(hub_banks), 1).otherwise(0)
)

# ══════════════════════════════════════════════════════════════
# FINAL FEATURE SET SUMMARY
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("📋 FINAL FEATURE SET")
print("=" * 55)

all_features = [
    # Group 1 — Transactional
    "is_cross_border", "hour_of_day", "is_peak_hour",
    "day_of_week", "is_weekend", "payment_format_risk",
    "currency_risk_score", "amount_log", "is_near_threshold",
    # Group 2 — Account Level
    "fan_out_degree", "fan_in_degree", "tx_velocity",
    "amount_per_tx", "amount_zscore_per_bank",
    "bank_risk_score", "is_high_fan_out",
    # Group 3 — Graph
    "is_in_cycle", "is_hub_bank"
]

print(f"\nTotal features built: {len(all_features)}")
for i, f in enumerate(all_features, 1):
    print(f"  {i:>2}. {f}")

# ══════════════════════════════════════════════════════════════
# VALIDATION — Key features vs laundering label
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("✅ FEATURE VALIDATION — Laundering vs Legitimate")
print("=" * 55)

key_features = [
    "is_in_cycle", "is_cross_border", "is_near_threshold",
    "is_weekend", "is_hub_bank", "is_high_fan_out",
    "payment_format_risk", "currency_risk_score"
]

print(f"\n{'Feature':<30} {'Laundering Avg':>15} {'Legitimate Avg':>15} {'Ratio':>8}")
print("-" * 72)
for feat in key_features:
    laund = trans_df.filter(col("Is Laundering") == 1) \
        .selectExpr(f"round(avg({feat}), 4) as v").collect()[0][0]
    legit = trans_df.filter(col("Is Laundering") == 0) \
        .selectExpr(f"round(avg({feat}), 4) as v").collect()[0][0]
    ratio = py_round(float(laund) / max(float(legit), 0.0001), 2)
    print(f"  {feat:<28} {str(laund):>15} {str(legit):>15} {ratio:>7}x")

# ══════════════════════════════════════════════════════════════
# SAVE FINAL FEATURE SET
# ══════════════════════════════════════════════════════════════
print("\n💾 Saving final feature set...")

# Select only what we need for model training
model_cols = all_features + [
    "Account", "To Account", "From Bank", "To Bank",
    "Amount Paid", "Timestamp", "Is Laundering"
]

final_df = trans_df.select(model_cols)

output_path = "/workspace/data/features_final.parquet"
final_df.write.mode("overwrite").parquet(output_path)

print(f"✅ Final feature set saved to {output_path}")
print(f"   Total rows     : {final_df.count():,}")
print(f"   Total columns  : {len(final_df.columns)}")
print(f"   Feature columns: {len(all_features)}")

print("\nFinal schema:")
final_df.printSchema()

spark.stop()
print("\n✅ Feature Engineering Complete! Ready for model training.")