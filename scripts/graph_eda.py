# ╔══════════════════════════════════════════════════════════════╗
# ║          AML Sentinel — Graph & Network EDA                 ║
# ║          Native Windows Version                             ║
# ╚══════════════════════════════════════════════════════════════╝

import sys
import os

# ── Config ─────────────────────────────────────────────────────
sys.path.append(r"C:\Users\VatsaL\Desktop\Datasets\AML_Sentinel")
from config import *

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, sum, avg, round, desc,
    countDistinct, when, max, min
)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np

# ── Spark Session ──────────────────────────────────────────────
spark = SparkSession.builder \
    .appName("AML_Graph_EDA") \
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
# 1. FAN-OUT DETECTION
# ══════════════════════════════════════════════════════════════
print("=" * 55)
print("1️⃣  FAN-OUT DETECTION (One Sender → Many Receivers)")
print("=" * 55)

fanout = trans_df.groupBy("Account", "Is Laundering") \
    .agg(
        countDistinct("To Account").alias("Unique Receivers"),
        count("*").alias("Total Transactions"),
        round(sum("Amount Paid"), 2).alias("Total Amount")
    )

fanout_stats = fanout.groupBy("Is Laundering").agg(
    round(avg("Unique Receivers"), 2).alias("Avg Unique Receivers"),
    round(avg("Total Transactions"), 2).alias("Avg Transactions"),
    max("Unique Receivers").alias("Max Unique Receivers")
).toPandas()
fanout_stats["Is Laundering"] = fanout_stats["Is Laundering"].map({0: "Legitimate", 1: "Laundering"})
print(fanout_stats.to_string(index=False))

print("\nTop 10 Fan-Out Laundering Accounts:")
top_fanout = fanout.filter(col("Is Laundering") == 1) \
    .orderBy(desc("Unique Receivers")).limit(10).toPandas()
print(top_fanout.to_string(index=False))

# ══════════════════════════════════════════════════════════════
# 2. FAN-IN DETECTION
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("2️⃣  FAN-IN DETECTION (Many Senders → One Receiver)")
print("=" * 55)

fanin = trans_df.groupBy("To Account", "Is Laundering") \
    .agg(
        countDistinct("Account").alias("Unique Senders"),
        count("*").alias("Total Transactions"),
        round(sum("Amount Paid"), 2).alias("Total Received")
    )

fanin_stats = fanin.groupBy("Is Laundering").agg(
    round(avg("Unique Senders"), 2).alias("Avg Unique Senders"),
    round(avg("Total Transactions"), 2).alias("Avg Transactions"),
    max("Unique Senders").alias("Max Unique Senders")
).toPandas()
fanin_stats["Is Laundering"] = fanin_stats["Is Laundering"].map({0: "Legitimate", 1: "Laundering"})
print(fanin_stats.to_string(index=False))

print("\nTop 10 Fan-In Laundering Accounts:")
top_fanin = fanin.filter(col("Is Laundering") == 1) \
    .orderBy(desc("Unique Senders")).limit(10).toPandas()
print(top_fanin.to_string(index=False))

# ══════════════════════════════════════════════════════════════
# 3. CIRCULAR TRANSACTION DETECTION
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("3️⃣  CIRCULAR TRANSACTION DETECTION (A→B→A Cycles)")
print("=" * 55)

self_loops = trans_df.filter(col("Account") == col("To Account"))
total_self = self_loops.count()
launder_self = self_loops.filter(col("Is Laundering") == 1).count()
print(f"Self-loop transactions (A→A)  : {total_self:,}")
print(f"Laundering self-loops         : {launder_self:,}")
if total_self > 0:
    print(f"Laundering rate in self-loops : {launder_self/total_self*100:.3f}%")

print("\nDetecting direct cycles (A→B AND B→A)...")
forward = trans_df.select(
    col("Account").alias("Sender"),
    col("To Account").alias("Receiver"),
    col("Is Laundering")
)
reverse = trans_df.select(
    col("To Account").alias("Sender"),
    col("Account").alias("Receiver")
)

cycles = forward.join(
    reverse,
    (forward.Sender == reverse.Sender) & (forward.Receiver == reverse.Receiver)
).filter(forward.Sender != forward.Receiver)

cycle_count = cycles.count()
cycle_launder = cycles.filter(col("Is Laundering") == 1).count()
print(f"Direct cycle transactions     : {cycle_count:,}")
print(f"Laundering in cycles          : {cycle_launder:,}")
if cycle_count > 0:
    print(f"Laundering rate in cycles     : {cycle_launder/cycle_count*100:.3f}%")

# ══════════════════════════════════════════════════════════════
# 4. STRUCTURING / SMURFING DETECTION
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("4️⃣  STRUCTURING / SMURFING DETECTION")
print("    (Transactions just below $10,000 threshold)")
print("=" * 55)

structuring = trans_df.withColumn(
    "Is Structured",
    when((col("Amount Paid") >= 8000) & (col("Amount Paid") < 10000), 1).otherwise(0)
)

struct_stats = structuring.groupBy("Is Structured", "Is Laundering") \
    .count().toPandas()

struct_pivot = struct_stats.pivot(
    index="Is Structured", columns="Is Laundering", values="count"
).fillna(0)
struct_pivot.columns = ["Legitimate", "Laundering"]
struct_pivot["Laundering Rate %"] = (
    struct_pivot["Laundering"] /
    (struct_pivot["Legitimate"] + struct_pivot["Laundering"]) * 100
).round(3)
struct_pivot.index = struct_pivot.index.map({0: "Other Amounts", 1: "$8K-$10K Range"})
print(struct_pivot.to_string())

# ══════════════════════════════════════════════════════════════
# 5. ACCOUNT TRANSACTION VELOCITY
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("5️⃣  ACCOUNT TRANSACTION VELOCITY")
print("=" * 55)

velocity = trans_df.groupBy("Account", "Is Laundering") \
    .agg(count("*").alias("Transaction Count"))

velocity_stats = velocity.groupBy("Is Laundering").agg(
    round(avg("Transaction Count"), 2).alias("Avg Txn Count"),
    max("Transaction Count").alias("Max Txn Count")
).toPandas()
velocity_stats["Is Laundering"] = velocity_stats["Is Laundering"].map({0: "Legitimate", 1: "Laundering"})
print(velocity_stats.to_string(index=False))

print("\nTop 10 Highest Velocity Laundering Accounts:")
top_velocity = velocity.filter(col("Is Laundering") == 1) \
    .orderBy(desc("Transaction Count")).limit(10).toPandas()
print(top_velocity.to_string(index=False))

# ══════════════════════════════════════════════════════════════
# 6. BANK-TO-BANK FLOW ANALYSIS
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("6️⃣  BANK-TO-BANK FLOW ANALYSIS")
print("=" * 55)

bank_flow = trans_df.filter(col("Is Laundering") == 1) \
    .groupBy("From Bank", "To Bank") \
    .agg(
        count("*").alias("Laundering Transactions"),
        round(sum("Amount Paid"), 2).alias("Total Amount")
    ) \
    .orderBy(desc("Laundering Transactions")).limit(10)

print("Top 10 Bank-to-Bank Laundering Flows:")
bank_flow.show(10, truncate=False)
bank_flow_pd = bank_flow.toPandas()

# ══════════════════════════════════════════════════════════════
# 7. GENERATE PLOTS
# ══════════════════════════════════════════════════════════════
print("\n📊 Generating Network EDA plots...")

plt.style.use("dark_background")
fig = plt.figure(figsize=(20, 20))
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

colors = ["#00D4AA", "#FF4B4B"]

ax1 = fig.add_subplot(gs[0, 0])
fanout_plot = fanout_stats.set_index("Is Laundering")["Avg Unique Receivers"]
fanout_plot.plot(kind="bar", ax=ax1, color=colors)
ax1.set_title("Avg Unique Receivers per Account\n(Fan-Out Detection)", fontsize=13, fontweight="bold")
ax1.set_ylabel("Avg Unique Receivers")
ax1.tick_params(axis="x", rotation=0)
for i, v in enumerate(fanout_plot):
    ax1.text(i, v + 0.05, f"{v:.2f}", ha="center", fontweight="bold")

ax2 = fig.add_subplot(gs[0, 1])
fanin_plot = fanin_stats.set_index("Is Laundering")["Avg Unique Senders"]
fanin_plot.plot(kind="bar", ax=ax2, color=colors)
ax2.set_title("Avg Unique Senders per Account\n(Fan-In Detection)", fontsize=13, fontweight="bold")
ax2.set_ylabel("Avg Unique Senders")
ax2.tick_params(axis="x", rotation=0)
for i, v in enumerate(fanin_plot):
    ax2.text(i, v + 0.05, f"{v:.2f}", ha="center", fontweight="bold")

ax3 = fig.add_subplot(gs[1, 0])
ax3.barh(top_fanout["Account"].astype(str), top_fanout["Unique Receivers"], color="#FF4B4B")
ax3.set_title("Top 10 Fan-Out Laundering Accounts", fontsize=13, fontweight="bold")
ax3.set_xlabel("Unique Receivers")

ax4 = fig.add_subplot(gs[1, 1])
ax4.barh(top_fanin["To Account"].astype(str), top_fanin["Unique Senders"], color="#FFB347")
ax4.set_title("Top 10 Fan-In Laundering Accounts", fontsize=13, fontweight="bold")
ax4.set_xlabel("Unique Senders")

ax5 = fig.add_subplot(gs[2, 0])
struct_pivot["Laundering Rate %"].plot(kind="bar", ax=ax5, color=["#00D4AA", "#FF4B4B"])
ax5.set_title("Structuring / Smurfing Detection\n($8K-$10K Threshold)", fontsize=13, fontweight="bold")
ax5.set_ylabel("Laundering Rate %")
ax5.tick_params(axis="x", rotation=0)

ax6 = fig.add_subplot(gs[2, 1])
bank_flow_pd["Bank Pair"] = bank_flow_pd["From Bank"] + " → " + bank_flow_pd["To Bank"]
ax6.barh(bank_flow_pd["Bank Pair"], bank_flow_pd["Laundering Transactions"], color="#9B59B6")
ax6.set_title("Top 10 Bank-to-Bank Laundering Flows", fontsize=13, fontweight="bold")
ax6.set_xlabel("Laundering Transactions")

plt.suptitle("AML Sentinel — Graph & Network EDA",
             fontsize=18, fontweight="bold", y=1.01)

plt.savefig(GRAPH_EDA, dpi=150, bbox_inches="tight")
print(f"✅ Plots saved to {GRAPH_EDA}")

spark.stop()
print("\n✅ Graph EDA Complete!")