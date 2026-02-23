# AML Sentinel — Project Notes & Findings
> Last Updated: February 20, 2026
> Author: Vatsal
> Purpose: Running notes for final report generation

---

## 🏗️ PROJECT ARCHITECTURE

```
Windows Machine (Host)
├── Data stays locally on Windows filesystem
└── Docker Container (aml_sentinel_container)
    ├── PySpark 4.1.1      → Big Data processing
    ├── PyTorch cu121      → GPU training
    ├── Unsloth            → LLM fine-tuning
    ├── Qwen 2.5 1.5B      → Explainable AI (XAI)
    └── Reads data via volume mount (no copying)
```

**Design Decision:** Data lives on Windows, Docker is purely a compute engine.
**Reason:** Avoids data duplication, easier file management, persistent storage.

---

## 💻 ENVIRONMENT SETUP

| Component | Version/Detail |
|-----------|---------------|
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| VRAM | 4.29 GB |
| CUDA (Host) | 12.9 |
| CUDA (Container) | 12.3 |
| PyTorch | cu121 (compatible with CUDA 12.3) |
| Java | OpenJDK 17 |
| PySpark | 4.1.1 |
| Base Image | nvcr.io/nvidia/pytorch:24.01-py3 |
| Container Size | ~36.6 GB |
| OS | Windows + Docker Desktop (WSL2) |

**Key Fix:** PyTorch must be installed with `--index-url https://download.pytorch.org/whl/cu121`
**Key Fix:** Unsloth installed with `--no-deps` to prevent torch version conflicts.
**Key Fix:** Java 17 required for PySpark 4.x (class file version 61.0).

---

## 📦 DATASET

| Property | Detail |
|----------|--------|
| Name | IBM Transactions for Anti Money Laundering (AML) |
| Variant | HI-Medium (High Illicit ratio) |
| Source | Kaggle — ealtman2019 |
| Files | HI-Medium_Trans.csv, HI-Medium_accounts.csv, HI-Medium_Patterns.txt |
| Trans File Size | 2.9 GB |
| Accounts File Size | 139 MB |
| Total Transactions | 31,898,238 (~32 million) |
| Storage Format | Parquet (converted from CSV for faster reads) |

**Why HI-Medium:** High Illicit ratio gives more labeled fraud cases for better model training.
**Why Parquet:** Significantly faster reads for iterative ML experimentation vs CSV.

---

## 📊 EDA FINDINGS

### 1. Class Imbalance
| Class | Count | Percentage |
|-------|-------|-----------|
| Legitimate | 31,863,008 | 99.89% |
| Money Laundering | 35,230 | 0.11% |

⚠️ **Critical:** Severe imbalance — a naive model predicting all legitimate gets 99.89% accuracy.
**Action Required:** Must use SMOTE, weighted loss functions, or undersampling techniques.

---

### 2. Transaction Amount Analysis
| Class | Avg Amount | Min | Max | Std Dev |
|-------|-----------|-----|-----|---------|
| Laundering | $53,116,745 | $0 | $906B | $4.99B |
| Legitimate | $4,363,705 | $0 | $8.16T | $1.84B |

⚠️ **Key Finding:** Laundering transactions are on average **12x larger** than legitimate ones.
**Feature Idea:** Amount thresholds, log-transformed amounts, amount z-scores per bank.

---

### 3. Payment Format Analysis
| Payment Format | Laundering Rate % |
|---------------|------------------|
| ACH | 0.795% |
| Bitcoin | 0.035% |
| Cash | 0.021% |
| Cheque | 0.018% |
| Credit Card | 0.015% |
| Reinvestment | 0.000% |
| Wire | 0.000% |

⚠️ **Key Finding:** ACH has **40x higher** laundering rate than other formats.
⚠️ **Key Finding:** Wire and Reinvestment have 0% laundering — launderers actively avoid these.
**Feature Idea:** Binary flag `is_ACH`, payment format encoding.

---

### 4. Currency Analysis
| Currency | Laundering Rate % |
|----------|------------------|
| UK Pound | 0.160% |
| Ruble | 0.149% |
| Euro | 0.133% |
| Yen | 0.130% |
| US Dollar | 0.122% |
| Yuan | 0.119% |
| Bitcoin | 0.035% |

⚠️ **Key Finding:** UK Pound and Ruble have highest laundering rates.
⚠️ **Surprising Finding:** Currency mismatch has **0% laundering rate** — launderers keep same currency to avoid detection flags.
**Feature Idea:** Currency risk score, `is_high_risk_currency` flag.

---

### 5. Temporal Patterns
**Peak Laundering Hours:**
| Hour | Laundering Rate % |
|------|------------------|
| 11am | 0.179% |
| 12pm | 0.178% |
| 1pm | 0.176% |
| 4pm | 0.166% |
| 2pm | 0.165% |

**Peak Laundering Days:**
| Day | Laundering Rate % |
|-----|------------------|
| Saturday | 0.284% |
| Sunday | 0.270% |
| Monday | 0.124% |

⚠️ **Key Finding:** Weekends (Sat/Sun) have **2x higher** laundering rate than weekdays.
⚠️ **Key Finding:** Lunch hours (11am-1pm) are peak laundering window.
**Hypothesis:** Launderers mimic normal business activity but exploit reduced weekend monitoring.
**Feature Idea:** `is_weekend`, `hour_of_day`, `is_peak_hour` flags.

---

### 6. Cross-Border Analysis
| Transaction Type | Laundering Rate % |
|-----------------|------------------|
| Cross-Border | 0.120% |
| Same Bank | 0.012% |

⚠️ **Key Finding:** Cross-border transactions are **10x more likely** to be laundering.
**Feature Idea:** `is_cross_border` binary flag — strong predictor.

---

### 7. Top Banks in Laundering
| Bank | Laundering Count |
|------|----------------|
| 070 | 4,190 |
| 020 | 300 |
| 000 | 280 |
| 011 | 245 |
| 012 | 206 |

⚠️ **Key Finding:** Bank 070 is a massive outlier with **14x more** laundering than the second bank.
**Action:** Flag Bank 070 as high-risk entity. Investigate if it's a hub bank in laundering networks.
**Feature Idea:** Bank risk score based on historical laundering involvement.

---

### 8. Currency Mismatch Analysis
| Type | Laundering Rate % |
|------|------------------|
| Same Currency | 0.112% |
| Currency Mismatch | 0.000% |

⚠️ **Surprising Finding:** No currency mismatch in laundering transactions.
**Hypothesis:** Launderers deliberately keep same currency to avoid triggering mismatch alerts.
**Implication:** Currency mismatch is NOT a useful feature for detection.

---

---

## 📊 GRAPH & NETWORK EDA FINDINGS

### 1. Basic Graph Statistics
| Metric | Value |
|--------|-------|
| Total Unique Accounts (Nodes) | TBD from output |
| Total Transactions (Edges) | 31,898,238 |
| Laundering Edges | 35,230 |

---

### 2. Fan-Out Detection (One Sender → Many Receivers)
| Class | Avg Unique Receivers | Max Unique Receivers |
|-------|---------------------|---------------------|
| Laundering | 1.46 | 1,484 |
| Legitimate | 2.21 | 55,953 |

⚠️ **Key Finding:** Account `100428660` sent to **1,484 unique receivers** totaling **$1 Billion** — classic layering pattern.
**Feature Idea:** `fan_out_degree`, `is_high_fan_out` flag (threshold >100 receivers).

---

### 3. Fan-In Detection (Many Senders → One Receiver)
| Class | Avg Unique Senders | Max Unique Senders |
|-------|-------------------|-------------------|
| Laundering | 1.25 | 23 |
| Legitimate | 2.64 | 2,304 |

⚠️ **Key Finding:** Account `824BF8940` received from **23 unique senders** — classic consolidation pattern.
**Feature Idea:** `fan_in_degree`, `is_high_fan_in` flag.

---

### 4. Circular Transaction Detection
| Type | Count | Laundering Rate |
|------|-------|----------------|
| Self-loops (A→A) | 2,561,860 | 0.003% |
| Direct Cycles (A→B and B→A) | 130,036 | **17.267%** |

⚠️ **CRITICAL FINDING:** Circular transactions have **17.267% laundering rate — 154x higher** than overall rate of 0.11%.
⚠️ This is the **single strongest predictor** found in the entire EDA.
**Feature Idea:** `is_in_cycle` binary flag — must be included in model.

---

### 5. Structuring / Smurfing Detection
| Amount Range | Laundering Rate |
|-------------|----------------|
| Other Amounts | 0.106% |
| $8K-$10K Range | **0.317%** |

⚠️ **Key Finding:** Transactions in $8K-$10K range have **3x higher** laundering rate.
**Hypothesis:** Launderers deliberately stay just below $10,000 reporting threshold (structuring/smurfing).
**Feature Idea:** `is_near_threshold` flag for amounts between $8K-$10K.

---

### 6. Account Transaction Velocity
| Class | Avg Transactions | Max Transactions |
|-------|-----------------|-----------------|
| Laundering | 1.55 | 1,524 |
| Legitimate | 15.83 | 1,075,455 |

⚠️ **Interesting Finding:** Laundering accounts have LOWER average velocity (1.55 vs 15.83).
**Hypothesis:** Launderers use many different accounts rather than one high-volume account to avoid detection.
**Feature Idea:** `tx_velocity`, `amount_per_tx` ratio.

---

### 7. Bank-to-Bank Flow Analysis
| Flow | Laundering Transactions | Total Amount |
|------|------------------------|-------------|
| 0272142 → 0272142 | 37 | **$3.88 Billion** |
| 0272142 → 0272896 | 33 | $56.5M |
| 0272896 → 0272142 | 30 | $22.5M |

⚠️ **Key Finding:** Bank `0272142` is a **major laundering hub** — self-cycling $3.88B and appearing in top 3 flows.
⚠️ Banks `0272142` and `0272896` are cycling money between each other (circular bank flow).
**Feature Idea:** `bank_laundering_risk_score`, `is_hub_bank` flag.

---

## 🎯 KEY FEATURES FOR ML MODEL
Based on ALL EDA findings, these features should be engineered:

**Transactional Features:**
1. `is_cross_border` — 10x higher laundering rate
2. `is_weekend` — 2x higher on weekends
3. `is_peak_hour` — 11am-1pm window
4. `payment_format_risk` — ACH = high risk
5. `currency_risk_score` — UK Pound, Ruble = high risk
6. `amount_log` — log transformed amount
7. `amount_zscore_per_bank` — unusual amounts per bank
8. `is_near_threshold` — $8K-$10K structuring window (3x rate)
9. `hour_of_day` — temporal feature
10. `day_of_week` — temporal feature

**Graph/Network Features:**
11. `is_in_cycle` — **STRONGEST FEATURE** (17.267% laundering rate, 154x overall)
12. `fan_out_degree` — number of unique receivers per sender
13. `fan_in_degree` — number of unique senders per receiver
14. `is_high_fan_out` — flag for >100 unique receivers
15. `bank_laundering_risk_score` — based on historical laundering rate per bank
16. `is_hub_bank` — flag for banks like 0272142
17. `tx_velocity` — transaction count per account
18. `amount_per_tx` — average amount per transaction

---

## ⚖️ CLASS IMBALANCE STRATEGY
- Technique to be decided: SMOTE / Weighted Loss / Undersampling
- Evaluation metric: F1 Score, Precision-Recall AUC (NOT accuracy)
- Reason: Accuracy is misleading with 99.89%/0.11% split

---

## 🤖 MODEL PLAN
| Component | Tool |
|-----------|------|
| Data Processing | PySpark |
| ML Detection Model | XGBoost / GNN (TBD) |
| Explainability | Qwen 2.5 1.5B via Unsloth |
| GPU Acceleration | RTX 3050 (4.29GB VRAM) |

---

## 📝 PENDING DECISIONS
- [ ] Choose between XGBoost vs GNN for detection
- [ ] Choose class imbalance strategy
- [ ] Design Qwen 2.5 prompt template for explanations
- [ ] Define evaluation metrics and thresholds

---

## 🐛 ISSUES & FIXES LOG
| Issue | Fix |
|-------|-----|
| `libcusparseLt.so.0` error | Reinstall PyTorch with cu121 wheels |
| `get_total_memory` AttributeError | Use `get_device_properties(0).total_memory` |
| Java version mismatch (55 vs 61) | Upgrade to OpenJDK 17 |
| Libraries lost after docker-compose up | Created Dockerfile to bake libs permanently |
| pandas 1.5.3 incompatible with PySpark 4 | Upgrade to pandas>=2.2.0 |
| `docker cp` permission denied | Copy to /tmp first, then move |