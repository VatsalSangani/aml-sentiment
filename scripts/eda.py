# ╔══════════════════════════════════════════════════════════════╗
# ║          AML Sentinel — Exploratory Data Analysis           ║
# ║          Native Windows Version                             ║
# ╚══════════════════════════════════════════════════════════════╝

import sys
import os

# ── Config ─────────────────────────────────────────────────────
sys.path.append(r"C:\Users\VatsaL\Desktop\Datasets\AML_Sentinel")
from config import *

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, sum, avg, min, max, round,
    hour, dayofweek, when, stddev, desc
)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import pandas as pd
import numpy as np

# ── Spark Session ──────────────────────────────────────────────
spark = SparkSession.builder \
    .appName("AML_EDA") \
    .config("spark.driver.memory", SPARK_DRIVER_MEMORY) \
    .config("spark.sql.shuffle.partitions", SPARK_SHUFFLE_PARTITIONS) \
    .config("spark.pyspark.python", PYSPARK_PYTHON) \
    .config("spark.pyspark.driver.python", PYSPARK_PYTHON) \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# ── Load Parquet ───────────────────────────────────────────────
print("📥 Loading Parquet files...")
trans_df = spark.read.parquet(TRANS_PARQUET)
trans_df = trans_df.withColumnRenamed("Account.1", "To Account")
print(f"✅ Loaded {trans_df.count():,} transactions\n")

# ══════════════════════════════════════════════════════════════
# 1. CLASS IMBALANCE
# ══════════════════════════════════════════════════════════════
print("=" * 55)
print("1️⃣  CLASS IMBALANCE")
print("=" * 55)

class_dist = trans_df.groupBy("Is Laundering").count().toPandas()
class_dist["label"] = class_dist["Is Laundering"].map({0: "Legitimate", 1: "Laundering"})
class_dist["pct"] = (class_dist["count"] / class_dist["count"].sum() * 100).round(3)
print(class_dist[["label", "count", "pct"]].to_string(index=False))

# ══════════════════════════════════════════════════════════════
# 2. TRANSACTION AMOUNT ANALYSIS
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("2️⃣  TRANSACTION AMOUNT ANALYSIS")
print("=" * 55)

amount_stats = trans_df.groupBy("Is Laundering").agg(
    round(avg("Amount Paid"), 2).alias("Avg Amount"),
    round(min("Amount Paid"), 2).alias("Min Amount"),
    round(max("Amount Paid"), 2).alias("Max Amount"),
    round(stddev("Amount Paid"), 2).alias("Std Dev"),
).toPandas()
amount_stats["Is Laundering"] = amount_stats["Is Laundering"].map({0: "Legitimate", 1: "Laundering"})
print(amount_stats.to_string(index=False))

# ══════════════════════════════════════════════════════════════
# 3. PAYMENT FORMAT ANALYSIS
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("3️⃣  PAYMENT FORMAT ANALYSIS")
print("=" * 55)

payment_analysis = trans_df.groupBy("Payment Format", "Is Laundering") \
    .count().orderBy("Payment Format", "Is Laundering").toPandas()

payment_pivot = payment_analysis.pivot(
    index="Payment Format", columns="Is Laundering", values="count"
).fillna(0)
payment_pivot.columns = ["Legitimate", "Laundering"]
payment_pivot["Laundering Rate %"] = (
    payment_pivot["Laundering"] /
    (payment_pivot["Legitimate"] + payment_pivot["Laundering"]) * 100
).round(3)
payment_pivot = payment_pivot.sort_values("Laundering Rate %", ascending=False)
print(payment_pivot.to_string())

# ══════════════════════════════════════════════════════════════
# 4. CURRENCY ANALYSIS
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("4️⃣  CURRENCY ANALYSIS")
print("=" * 55)

currency_analysis = trans_df.groupBy("Payment Currency", "Is Laundering") \
    .count().orderBy("Payment Currency").toPandas()

currency_pivot = currency_analysis.pivot(
    index="Payment Currency", columns="Is Laundering", values="count"
).fillna(0)
currency_pivot.columns = ["Legitimate", "Laundering"]
currency_pivot["Laundering Rate %"] = (
    currency_pivot["Laundering"] /
    (currency_pivot["Legitimate"] + currency_pivot["Laundering"]) * 100
).round(3)
currency_pivot = currency_pivot.sort_values("Laundering Rate %", ascending=False)
print(currency_pivot.to_string())

# ══════════════════════════════════════════════════════════════
# 5. TEMPORAL ANALYSIS
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("5️⃣  TEMPORAL ANALYSIS")
print("=" * 55)

hourly = trans_df.withColumn("Hour", hour("Timestamp")) \
    .groupBy("Hour", "Is Laundering").count() \
    .orderBy("Hour").toPandas()

hourly_pivot = hourly.pivot(
    index="Hour", columns="Is Laundering", values="count"
).fillna(0)
hourly_pivot.columns = ["Legitimate", "Laundering"]
hourly_pivot["Laundering Rate %"] = (
    hourly_pivot["Laundering"] /
    (hourly_pivot["Legitimate"] + hourly_pivot["Laundering"]) * 100
).round(3)

top_hours = hourly_pivot.nlargest(5, "Laundering Rate %")
print("Top 5 Peak Laundering Hours:")
print(top_hours[["Laundering Rate %"]].to_string())

daily = trans_df.withColumn("DayOfWeek", dayofweek("Timestamp")) \
    .groupBy("DayOfWeek", "Is Laundering").count() \
    .orderBy("DayOfWeek").toPandas()

daily_pivot = daily.pivot(
    index="DayOfWeek", columns="Is Laundering", values="count"
).fillna(0)
daily_pivot.columns = ["Legitimate", "Laundering"]
daily_pivot["Laundering Rate %"] = (
    daily_pivot["Laundering"] /
    (daily_pivot["Legitimate"] + daily_pivot["Laundering"]) * 100
).round(3)
day_names = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
daily_pivot.index = daily_pivot.index.map(day_names)
print("\nLaundering Rate by Day of Week:")
print(daily_pivot[["Laundering Rate %"]].to_string())

# ══════════════════════════════════════════════════════════════
# 6. CROSS-BORDER ANALYSIS
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("6️⃣  CROSS-BORDER TRANSACTION ANALYSIS")
print("=" * 55)

cross_border = trans_df.withColumn(
    "Is Cross Border",
    when(col("From Bank") != col("To Bank"), 1).otherwise(0)
).groupBy("Is Cross Border", "Is Laundering").count().toPandas()

cross_pivot = cross_border.pivot(
    index="Is Cross Border", columns="Is Laundering", values="count"
).fillna(0)
cross_pivot.columns = ["Legitimate", "Laundering"]
cross_pivot["Laundering Rate %"] = (
    cross_pivot["Laundering"] /
    (cross_pivot["Legitimate"] + cross_pivot["Laundering"]) * 100
).round(3)
cross_pivot.index = cross_pivot.index.map({0: "Same Bank", 1: "Cross Border"})
print(cross_pivot.to_string())

# ══════════════════════════════════════════════════════════════
# 7. TOP BANKS
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("7️⃣  TOP 10 BANKS INVOLVED IN LAUNDERING")
print("=" * 55)

top_banks = trans_df.filter(col("Is Laundering") == 1) \
    .groupBy("From Bank").count() \
    .orderBy(desc("count")).limit(10).toPandas()
print(top_banks.to_string(index=False))

# ══════════════════════════════════════════════════════════════
# 8. CURRENCY MISMATCH
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("8️⃣  CURRENCY MISMATCH ANALYSIS")
print("=" * 55)

currency_mismatch = trans_df.withColumn(
    "Currency Mismatch",
    when(col("Payment Currency") != col("Receiving Currency"), 1).otherwise(0)
).groupBy("Currency Mismatch", "Is Laundering").count().toPandas()

mismatch_pivot = currency_mismatch.pivot(
    index="Currency Mismatch", columns="Is Laundering", values="count"
).fillna(0)
mismatch_pivot.columns = ["Legitimate", "Laundering"]
mismatch_pivot["Laundering Rate %"] = (
    mismatch_pivot["Laundering"] /
    (mismatch_pivot["Legitimate"] + mismatch_pivot["Laundering"]) * 100
).round(3)
mismatch_pivot.index = mismatch_pivot.index.map({0: "Same Currency", 1: "Currency Mismatch"})
print(mismatch_pivot.to_string())

# ══════════════════════════════════════════════════════════════
# 9. GENERATE PLOTS
# ══════════════════════════════════════════════════════════════
print("\n📊 Generating plots...")

plt.style.use("dark_background")
fig = plt.figure(figsize=(20, 24))
gs = gridspec.GridSpec(4, 2, figure=fig, hspace=0.4, wspace=0.3)

ax1 = fig.add_subplot(gs[0, 0])
colors = ["#00D4AA", "#FF4B4B"]
ax1.pie(class_dist["count"], labels=class_dist["label"],
        autopct="%1.2f%%", colors=colors, startangle=90)
ax1.set_title("Class Distribution", fontsize=14, fontweight="bold")

ax2 = fig.add_subplot(gs[0, 1])
payment_pivot["Laundering Rate %"].plot(kind="bar", ax=ax2, color="#FF4B4B")
ax2.set_title("Laundering Rate by Payment Format", fontsize=14, fontweight="bold")
ax2.set_ylabel("Laundering Rate %")
ax2.tick_params(axis="x", rotation=45)

ax3 = fig.add_subplot(gs[1, 0])
currency_pivot["Laundering Rate %"].head(10).plot(kind="bar", ax=ax3, color="#FFB347")
ax3.set_title("Top 10 Currencies by Laundering Rate", fontsize=14, fontweight="bold")
ax3.set_ylabel("Laundering Rate %")
ax3.tick_params(axis="x", rotation=45)

ax4 = fig.add_subplot(gs[1, 1])
ax4.plot(hourly_pivot.index, hourly_pivot["Laundering Rate %"],
         color="#00D4AA", linewidth=2, marker="o", markersize=4)
ax4.set_title("Laundering Rate by Hour of Day", fontsize=14, fontweight="bold")
ax4.set_xlabel("Hour")
ax4.set_ylabel("Laundering Rate %")
ax4.set_xticks(range(0, 24))

ax5 = fig.add_subplot(gs[2, 0])
daily_pivot["Laundering Rate %"].plot(kind="bar", ax=ax5, color="#9B59B6")
ax5.set_title("Laundering Rate by Day of Week", fontsize=14, fontweight="bold")
ax5.set_ylabel("Laundering Rate %")
ax5.tick_params(axis="x", rotation=0)

ax6 = fig.add_subplot(gs[2, 1])
cross_pivot["Laundering Rate %"].plot(kind="bar", ax=ax6, color="#3498DB")
ax6.set_title("Laundering Rate: Cross-Border vs Same Bank", fontsize=14, fontweight="bold")
ax6.set_ylabel("Laundering Rate %")
ax6.tick_params(axis="x", rotation=0)

ax7 = fig.add_subplot(gs[3, 0])
sns.barplot(data=top_banks, x="count", y="From Bank", ax=ax7, palette="Reds_r")
ax7.set_title("Top 10 Banks in Laundering Transactions", fontsize=14, fontweight="bold")
ax7.set_xlabel("Count")

ax8 = fig.add_subplot(gs[3, 1])
mismatch_pivot["Laundering Rate %"].plot(kind="bar", ax=ax8, color="#E74C3C")
ax8.set_title("Laundering Rate: Currency Mismatch", fontsize=14, fontweight="bold")
ax8.set_ylabel("Laundering Rate %")
ax8.tick_params(axis="x", rotation=0)

plt.suptitle("AML Sentinel — Exploratory Data Analysis",
             fontsize=18, fontweight="bold", y=1.01)

plt.savefig(EDA_REPORT, dpi=150, bbox_inches="tight")
print(f"✅ Plots saved to {EDA_REPORT}")

spark.stop()
print("\n✅ EDA Complete!")