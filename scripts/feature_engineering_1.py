from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, hour, dayofweek, log1p, when,
    round, lit
)
import os

# ── Spark Session ──────────────────────────────────────────────
spark = SparkSession.builder \
    .appName("AML_Features_1_Transactional") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "8") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# ── Load Parquet ───────────────────────────────────────────────
print("📥 Loading transaction parquet...")
trans_df = spark.read.parquet("/workspace/data/trans_medium.parquet")
trans_df = trans_df.withColumnRenamed("Account.1", "To Account")
print(f"✅ Loaded {trans_df.count():,} transactions\n")

# ══════════════════════════════════════════════════════════════
# FEATURE 1: is_cross_border
# From EDA: Cross-border = 10x higher laundering rate
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 1: is_cross_border")
trans_df = trans_df.withColumn(
    "is_cross_border",
    when(col("From Bank") != col("To Bank"), 1).otherwise(0)
)

# ══════════════════════════════════════════════════════════════
# FEATURE 2: hour_of_day
# Raw hour extracted from timestamp
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 2: hour_of_day")
trans_df = trans_df.withColumn(
    "hour_of_day",
    hour(col("Timestamp"))
)

# ══════════════════════════════════════════════════════════════
# FEATURE 3: is_peak_hour
# From EDA: 11am-1pm has highest laundering rate (0.176-0.179%)
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 3: is_peak_hour")
trans_df = trans_df.withColumn(
    "is_peak_hour",
    when(col("hour_of_day").between(11, 13), 1).otherwise(0)
)

# ══════════════════════════════════════════════════════════════
# FEATURE 4: day_of_week
# 1=Sunday, 2=Monday ... 7=Saturday
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 4: day_of_week")
trans_df = trans_df.withColumn(
    "day_of_week",
    dayofweek(col("Timestamp"))
)

# ══════════════════════════════════════════════════════════════
# FEATURE 5: is_weekend
# From EDA: Sat(0.284%) and Sun(0.270%) = 2x higher rate
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 5: is_weekend")
trans_df = trans_df.withColumn(
    "is_weekend",
    when(col("day_of_week").isin(1, 7), 1).otherwise(0)
)

# ══════════════════════════════════════════════════════════════
# FEATURE 6: payment_format_risk
# From EDA: ACH=0.795%, Bitcoin=0.035%, Cash=0.021%
# Score: ACH=3, Bitcoin=2, Cash/Cheque/CreditCard=1, Wire/Reinvestment=0
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 6: payment_format_risk")
trans_df = trans_df.withColumn(
    "payment_format_risk",
    when(col("Payment Format") == "ACH",          3)
    .when(col("Payment Format") == "Bitcoin",     2)
    .when(col("Payment Format") == "Cash",        1)
    .when(col("Payment Format") == "Cheque",      1)
    .when(col("Payment Format") == "Credit Card", 1)
    .when(col("Payment Format") == "Wire",        0)
    .when(col("Payment Format") == "Reinvestment",0)
    .otherwise(1)
)

# ══════════════════════════════════════════════════════════════
# FEATURE 7: currency_risk_score
# From EDA laundering rates per currency:
# UK Pound=0.160, Ruble=0.149, Euro=0.133, Yen=0.130
# US Dollar=0.122, Yuan=0.119, Rupee=0.112
# Australian=0.080, Canadian=0.056, Shekel=0.047
# Brazil=0.044, Mexican=0.041, Saudi=0.040, Swiss=0.039, Bitcoin=0.035
# Scored 1-5 based on risk tier
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 7: currency_risk_score")
trans_df = trans_df.withColumn(
    "currency_risk_score",
    when(col("Payment Currency").isin("UK Pound", "Ruble"),                         5)
    .when(col("Payment Currency").isin("Euro", "Yen"),                              4)
    .when(col("Payment Currency").isin("US Dollar", "Yuan", "Rupee"),               3)
    .when(col("Payment Currency").isin("Australian Dollar", "Canadian Dollar"),     2)
    .when(col("Payment Currency").isin(
        "Shekel", "Brazil Real", "Mexican Peso",
        "Saudi Riyal", "Swiss Franc", "Bitcoin"),                                   1)
    .otherwise(2)
)

# ══════════════════════════════════════════════════════════════
# FEATURE 8: amount_log
# Log transform to handle extreme skew in transaction amounts
# log1p = log(x + 1) to handle zeros safely
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 8: amount_log")
trans_df = trans_df.withColumn(
    "amount_log",
    round(log1p(col("Amount Paid")), 4)
)

# ══════════════════════════════════════════════════════════════
# FEATURE 9: is_near_threshold
# From EDA: $8K-$10K range has 3x higher laundering rate (structuring)
# ══════════════════════════════════════════════════════════════
print("⚙️  Building Feature 9: is_near_threshold")
trans_df = trans_df.withColumn(
    "is_near_threshold",
    when(
        (col("Amount Paid") >= 8000) & (col("Amount Paid") < 10000), 1
    ).otherwise(0)
)

# ══════════════════════════════════════════════════════════════
# VALIDATION — Check features look correct
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("✅ FEATURE VALIDATION")
print("=" * 55)

feature_cols = [
    "is_cross_border", "hour_of_day", "is_peak_hour",
    "day_of_week", "is_weekend", "payment_format_risk",
    "currency_risk_score", "amount_log", "is_near_threshold",
    "Is Laundering"
]

print("\nSample rows with new features:")
trans_df.select(feature_cols).show(5)

print("\nFeature stats for Laundering vs Legitimate:")
for feat in ["is_cross_border", "is_weekend", "is_peak_hour",
             "payment_format_risk", "currency_risk_score",
             "is_near_threshold"]:
    laund_avg = trans_df.filter(col("Is Laundering") == 1) \
                        .selectExpr(f"round(avg({feat})*100, 3) as pct").collect()[0][0]
    legit_avg = trans_df.filter(col("Is Laundering") == 0) \
                        .selectExpr(f"round(avg({feat})*100, 3) as pct").collect()[0][0]
    print(f"  {feat:<25} Laundering: {laund_avg:>7}%  |  Legitimate: {legit_avg:>7}%")

# ══════════════════════════════════════════════════════════════
# SAVE — Output for Feature Engineering Script 2
# ══════════════════════════════════════════════════════════════
print("\n💾 Saving features_1 parquet...")
output_path = "/workspace/data/features_1.parquet"
trans_df.write.mode("overwrite").parquet(output_path)
print(f"✅ Saved to {output_path}")
print(f"   Total columns: {len(trans_df.columns)}")
print(f"   New features added: 9")

spark.stop()
print("\n✅ Feature Engineering Group 1 Complete!")