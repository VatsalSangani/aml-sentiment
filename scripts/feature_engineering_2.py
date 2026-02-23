from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, countDistinct, sum, avg,
    round, stddev, when, desc
)
from pyspark.sql.window import Window
import os

# ── Spark Session ──────────────────────────────────────────────
spark = SparkSession.builder \
    .appName("AML_Features_2_AccountLevel") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "8") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# ── Load from Feature Group 1 output ──────────────────────────
print("📥 Loading features_1 parquet...")
trans_df = spark.read.parquet("/workspace/data/features_1.parquet")
print(f"✅ Loaded {trans_df.count():,} transactions\n")

# ══════════════════════════════════════════════════════════════
# FEATURE 10: fan_out_degree
# How many unique receivers does each sender account have?
# Higher = more dispersal = suspicious
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 10: fan_out_degree")
fan_out = trans_df.groupBy("Account").agg(
    countDistinct("To Account").alias("fan_out_degree"),
    count("*").alias("tx_velocity"),
    round(sum("Amount Paid"), 2).alias("total_sent"),
    round(avg("Amount Paid"), 2).alias("avg_sent")
)
trans_df = trans_df.join(fan_out, on="Account", how="left")

# ══════════════════════════════════════════════════════════════
# FEATURE 11: fan_in_degree
# How many unique senders does each receiver account have?
# Higher = more consolidation = suspicious
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 11: fan_in_degree")
fan_in = trans_df.groupBy("To Account").agg(
    countDistinct("Account").alias("fan_in_degree"),
    round(sum("Amount Paid"), 2).alias("total_received"),
    round(avg("Amount Paid"), 2).alias("avg_received")
)
trans_df = trans_df.join(fan_in, on="To Account", how="left")

# ══════════════════════════════════════════════════════════════
# FEATURE 12: tx_velocity (already computed in fan_out)
# Total transaction count per sender account
# From EDA: Laundering avg=1.55 vs Legitimate avg=15.83
# ══════════════════════════════════════════════════════════════
print("⚙️  Feature 12: tx_velocity (computed in fan_out step)")

# ══════════════════════════════════════════════════════════════
# FEATURE 13: amount_per_tx
# Average amount per transaction for this account
# Laundering accounts tend to have higher amounts per tx
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 13: amount_per_tx")
trans_df = trans_df.withColumn(
    "amount_per_tx",
    round(col("total_sent") / when(col("tx_velocity") > 0,
          col("tx_velocity")).otherwise(1), 2)
)

# ══════════════════════════════════════════════════════════════
# FEATURE 14: amount_zscore_per_bank
# How unusual is this transaction amount compared to
# the average amount for this bank?
# z = (amount - bank_mean) / bank_std
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 14: amount_zscore_per_bank")
bank_stats = trans_df.groupBy("From Bank").agg(
    round(avg("Amount Paid"), 2).alias("bank_avg_amount"),
    round(stddev("Amount Paid"), 2).alias("bank_std_amount")
)
trans_df = trans_df.join(bank_stats, on="From Bank", how="left")
trans_df = trans_df.withColumn(
    "amount_zscore_per_bank",
    round(
        (col("Amount Paid") - col("bank_avg_amount")) /
        when(col("bank_std_amount") > 0,
             col("bank_std_amount")).otherwise(1),
        4
    )
)

# ══════════════════════════════════════════════════════════════
# FEATURE 15: bank_risk_score
# Historical laundering rate per bank (from EDA)
# Computed as: laundering_count / total_transactions per bank
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 15: bank_risk_score")
bank_risk = trans_df.groupBy("From Bank").agg(
    count("*").alias("bank_total_tx"),
    sum("Is Laundering").alias("bank_laund_tx")
)
bank_risk = bank_risk.withColumn(
    "bank_risk_score",
    round(
        col("bank_laund_tx") / when(col("bank_total_tx") > 0,
            col("bank_total_tx")).otherwise(1) * 100,
        6
    )
)
trans_df = trans_df.join(
    bank_risk.select("From Bank", "bank_risk_score"),
    on="From Bank", how="left"
)

# ══════════════════════════════════════════════════════════════
# FEATURE 16: is_high_fan_out
# Binary flag: fan_out_degree > 100
# From EDA: Account 100428660 had 1484 receivers = $1B laundering
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 16: is_high_fan_out")
trans_df = trans_df.withColumn(
    "is_high_fan_out",
    when(col("fan_out_degree") > 100, 1).otherwise(0)
)

# ══════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("✅ FEATURE VALIDATION")
print("=" * 55)

new_features = [
    "fan_out_degree", "fan_in_degree", "tx_velocity",
    "amount_per_tx", "amount_zscore_per_bank",
    "bank_risk_score", "is_high_fan_out"
]

print("\nSample rows with new features:")
trans_df.select(new_features + ["Is Laundering"]).show(5)

print("\nFeature averages — Laundering vs Legitimate:")
for feat in new_features:
    laund_avg = trans_df.filter(col("Is Laundering") == 1) \
        .selectExpr(f"round(avg({feat}), 4) as avg").collect()[0][0]
    legit_avg = trans_df.filter(col("Is Laundering") == 0) \
        .selectExpr(f"round(avg({feat}), 4) as avg").collect()[0][0]
    print(f"  {feat:<30} Laundering: {str(laund_avg):>12}  |  Legitimate: {str(legit_avg):>12}")

# ══════════════════════════════════════════════════════════════
# SAVE — Output for Feature Engineering Script 3
# ══════════════════════════════════════════════════════════════
print("\n💾 Saving features_2 parquet...")

# Drop intermediate columns not needed as features
cols_to_drop = ["bank_avg_amount", "bank_std_amount",
                "bank_total_tx", "bank_laund_tx"]
for c in cols_to_drop:
    if c in trans_df.columns:
        trans_df = trans_df.drop(c)

output_path = "/workspace/data/features_2.parquet"
trans_df.write.mode("overwrite").parquet(output_path)
print(f"✅ Saved to {output_path}")
print(f"   Total columns: {len(trans_df.columns)}")
print(f"   New features added: 7")

spark.stop()
print("\n✅ Feature Engineering Group 2 Complete!")