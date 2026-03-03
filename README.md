# AML Sentinel — Anti-Money Laundering Detection System

> End-to-end AML detection pipeline built on 31.9 million real financial transactions.  
> XGBoost + LightGBM ensemble model with Qwen 2.5 1.5B explainability and a React compliance dashboard.

---

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Architecture Overview](#architecture-overview)
- [Dataset](#dataset)
- [Project Structure](#project-structure)
- [Setup & Running](#setup--running)
- [Live Demo](#live-demo)
- [Technical Decisions — Q&A](#technical-decisions--qa)
  - [Why XGBoost + LightGBM and not a neural network?](#why-xgboost--lightgbm-and-not-a-neural-network)
  - [Why an ensemble and not just one model?](#why-an-ensemble-and-not-just-one-model)
  - [Why temporal split and not random split?](#why-temporal-split-and-not-random-split)
  - [Why AUC-PR and not accuracy?](#why-auc-pr-and-not-accuracy)
  - [Why SHAP for explainability?](#why-shap-for-explainability)
  - [Why Qwen 2.5 1.5B for the AI explanation?](#why-qwen-25-15b-for-the-ai-explanation)
  - [Why not fine-tune Qwen on your own data?](#why-not-fine-tune-qwen-on-your-own-data)
  - [Why not SMOTE for class imbalance?](#why-not-smote-for-class-imbalance)
  - [Why 3-layer imbalance handling?](#why-3-layer-imbalance-handling)
  - [Why threshold 0.8514 and not the default 0.5?](#why-threshold-08514-and-not-the-default-05)
  - [Why PySpark for data processing?](#why-pyspark-for-data-processing)
  - [Why Parquet and not CSV?](#why-parquet-and-not-csv)
  - [Why FastAPI for the backend?](#why-fastapi-for-the-backend)
  - [Why React for the frontend?](#why-react-for-the-frontend)
  - [How did you prevent data leakage?](#how-did-you-prevent-data-leakage)
  - [Why 18 features specifically?](#why-18-features-specifically)
  - [What is the circular transaction pattern and why is it so strong?](#what-is-the-circular-transaction-pattern-and-why-is-it-so-strong)
  - [Why does the model miss some fraud cases?](#why-does-the-model-miss-some-fraud-cases)
  - [What would you do differently in production?](#what-would-you-do-differently-in-production)
- [Model Performance](#model-performance)
- [Key EDA Findings](#key-eda-findings)
- [Feature Engineering](#feature-engineering)
- [XAI Design — Plain English Explanations](#xai-design--plain-english-explanations)
- [Known Limitations](#known-limitations)

---

## What This Project Does

AML Sentinel is a complete anti-money laundering detection system that takes raw financial transaction data and produces:

1. **A risk score** (0–1) for every transaction using an XGBoost + LightGBM ensemble trained on 31.9 million real transactions
2. **SHAP-based feature attribution** explaining which signals drove the score
3. **A plain-English compliance report** written by Qwen 2.5 1.5B, designed for investigators — no technical jargon, no ML terms
4. **A React dashboard** for compliance officers to analyze live transactions and review pre-generated case studies

---

## Architecture Overview

```
IBM AML Dataset (31.9M transactions, 2.9 GB CSV)
        │
        ▼
PySpark — Data Ingestion + Feature Engineering
        │  18 features: transactional + graph/network
        │
        ▼
XGBoost + LightGBM Ensemble (GPU — RTX 3050)
        │  AUC-ROC: 0.9857 | Recall: 81.23%
        │  Threshold: 0.8514 (tuned on Precision-Recall curve)
        │
        ▼
SHAP TreeExplainer — Feature Attribution
        │  Top 5 drivers per transaction
        │
        ▼
Qwen 2.5 1.5B (4-bit NF4 quantized, 1.17 GB VRAM)
        │  Plain-English compliance report
        │  No SHAP values, no feature names in output
        │
        ▼
FastAPI Backend (localhost:8000)
        │  POST /analyze — live scoring + explanation
        │  GET  /reports — 30 pre-generated XAI cases
        │  GET  /stats   — model performance metrics
        │
        ▼
React Dashboard (localhost:3000)
        Transaction Analyzer | XAI Report Viewer | Model Performance
```

---

## Dataset

**IBM Transactions for Anti Money Laundering (AML)**  
Source: [Kaggle — ealtman2019](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml)  
Variant: HI-Medium (High Illicit ratio)

| Property | Value |
|---|---|
| Total transactions | 31,898,238 (~32 million) |
| Laundering transactions | 35,230 (0.11%) |
| Legitimate transactions | 31,863,008 (99.89%) |
| Transaction file size | 2.9 GB |
| Time period | Multi-year synthetic bank data |

**Why HI-Medium?** The High Illicit variant has more labeled fraud cases, which gives the model more signal to learn from. The LI (Low Illicit) variant is more realistic but harder to train on with limited GPU resources.

---

## Project Structure

```
AML_Sentinel/
├── data/                        ← dataset (not committed — too large)
│   └── parquet/                 ← converted from CSV for faster reads
├── models/                      ← saved model files (not committed)
│   ├── xgb_model.json
│   ├── lgb_model.txt
│   └── ensemble_weights.json
├── notebooks/
│   ├── AML_Feature_Engineering.ipynb
│   ├── AML_Model_Training.ipynb
│   └── AML_XAI.ipynb
├── scripts/
│   ├── ingest.py                ← CSV → Parquet via PySpark
│   ├── eda.py                   ← exploratory data analysis
│   ├── graph_eda.py             ← network/graph EDA
│   └── hardware_check.py       ← GPU/CUDA verification
├── backend/
│   ├── main.py                  ← FastAPI app + all endpoints
│   ├── model_service.py         ← XGBoost + LightGBM + SHAP
│   ├── xai_service.py           ← Qwen load-on-demand + prompt pipeline
│   └── schemas.py               ← Pydantic request/response models
├── dashboard/
│   └── src/
│       ├── AML_Sentinel_Dashboard.jsx   ← main React component
│       └── api.js                       ← FastAPI client
├── config.py                    ← paths + Spark session factory
└── requirements.txt
```

---

## Setup & Running

### Prerequisites

```
Python 3.12+
Node.js 18+
NVIDIA GPU with CUDA 12.x (for Qwen inference)
CUDA toolkit installed
Java 17 (for PySpark)
```

### 1. Install dependencies

```bash
# Clone the repo
git clone https://github.com/yourusername/aml-sentinel.git
cd aml-sentinel

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Download the dataset

Download the IBM AML dataset (HI-Medium) from Kaggle and place the files in `data/raw/`:
```
data/raw/HI-Medium_Trans.csv
data/raw/HI-Medium_Accounts.csv
```

### 3. Run the notebooks in order

```
1. AML_Feature_Engineering.ipynb  — processes data, builds 18 features, saves parquet
2. AML_Model_Training.ipynb       — trains XGBoost + LightGBM, saves models
3. AML_XAI.ipynb                  — generates 30 XAI case reports using Qwen
```

### 4. Start the backend

```bash
cd backend
python main.py
# → http://localhost:8000
# → http://localhost:8000/docs   (Swagger UI)
```

### 5. Start the dashboard

```bash
cd dashboard
npm install
npm start
# → http://localhost:3000
```

---
## Live Demo

[![Open in HuggingFace Spaces](https://img.shields.io/badge/🤗%20HuggingFace-Live%20Demo-blue)](https://huggingface.co/spaces/brendvat/AML_Setinel)

> **Try it live** → [huggingface.co/spaces/brendvat/AML_Setinel](https://huggingface.co/spaces/brendvat/AML_Setinel)

The deployed version runs XGBoost + LightGBM inference on CPU (HuggingFace free tier).
Qwen 2.5 1.5B generates plain-English explanations on-demand.

---

## Technical Decisions — Q&A

This section answers the most likely questions about every significant design choice in the project.

---

### Why XGBoost + LightGBM and not a neural network?

Three reasons: explainability, performance on tabular data, and hardware constraints.

Neural networks (MLPs, transformers) are black boxes. In AML, every flag must be explainable to a compliance officer and potentially a regulator. XGBoost and LightGBM produce feature importances natively and work directly with SHAP — this is not possible with deep learning without significant additional tooling.

On tabular data with mixed feature types (binary flags, log-transformed amounts, counts), gradient boosting consistently outperforms neural networks in the literature. This is not a vision or NLP task where deep learning has a clear advantage.

Finally, our GPU has 4.29 GB VRAM. A deep learning model large enough to be competitive on 32M rows would likely not fit alongside Qwen 2.5 1.5B. Gradient boosting models are extremely memory-efficient.

**What about Graph Neural Networks (GNNs)?**  
GNNs would theoretically be the best model here since money laundering is fundamentally a graph problem. However, GNNs require the full transaction graph to be loaded into memory during inference, which is impractical for a 32M node graph on 4.29 GB VRAM. We instead extracted the most valuable graph signals (circular patterns, fan-out degree, hub bank detection) as static features and fed them into the gradient boosting models — getting much of the benefit without the infrastructure cost.

---

### Why an ensemble and not just one model?

XGBoost (depth-wise tree growth) and LightGBM (leaf-wise tree growth) make systematically different errors. When one model misses a laundering pattern, the other frequently catches it. Averaging their probability outputs reduces variance without increasing bias.

In practice, our equal-weight ensemble (0.5 XGB + 0.5 LGB) achieved AUC-PR of 0.3857, which exceeded either model individually. In fraud detection, even a 2–3% improvement in AUC-PR translates to thousands of additional fraud cases caught.

---

### Why temporal split and not random split?

Random splitting would be silent data leakage. In a random split, the training set contains transactions from the same time period as the test set — the model effectively sees the future. In production, the model will only ever see past transactions when scoring a new one.

Temporal split (train on earlier dates, test on later dates) simulates real deployment accurately. It tests whether the model generalises to new time periods, which is the only honest measure of real-world performance. Regulatory validation also explicitly requires out-of-time testing.

---

### Why AUC-PR and not accuracy?

A model that predicts "all legitimate" for every transaction achieves 99.89% accuracy on this dataset. That model catches zero fraud. Accuracy is completely meaningless for severely imbalanced classification.

AUC-PR (Area Under the Precision-Recall Curve) focuses entirely on the minority class. The baseline (random classifier) AUC-PR equals the class prevalence — 0.11% in our case. Our model achieved 0.3857, which is 35x better than random. This is the only metric that honestly reflects model quality on imbalanced data.

We also track recall as the primary operational metric because in AML, missing a fraud case (false negative) has a much higher cost than a false alarm (false positive). An investigator can review a false alarm in minutes. An undetected laundering scheme can run for years.

---

### Why SHAP for explainability?

SHAP (SHapley Additive exPlanations) provides mathematically grounded feature attributions based on game theory. For each transaction, SHAP tells us exactly how much each feature pushed the score up or down and by how much.

The alternatives — LIME (Local Interpretable Model-agnostic Explanations) and plain feature importance — both have significant drawbacks. LIME approximates locally and can be unstable between runs. Feature importance only tells you which features matter globally across the whole dataset, not for a specific transaction.

SHAP TreeExplainer is also extremely fast for tree models — it runs in O(TLD) time (where T is trees, L is leaves, D is depth) rather than requiring expensive model calls.

---

### Why Qwen 2.5 1.5B for the AI explanation?

Qwen 2.5 1.5B hits the right balance between capability and hardware constraint. At 4-bit NF4 quantization it uses 1.17 GB VRAM — the largest model that fits alongside our ML models on a 4.29 GB GPU.

We specifically chose it over alternatives for these reasons:

| Model | VRAM (4-bit) | Quality | Decision |
|---|---|---|---|
| Qwen 2.5 0.5B | ~0.4 GB | Too simple, repetitive outputs | Rejected |
| Qwen 2.5 1.5B | ~1.17 GB | Good reasoning, structured output | **Selected** |
| Qwen 2.5 3B | ~2.0 GB | Better but too tight with ML models | Rejected |
| Llama 3.2 1B | ~0.8 GB | Weaker instruction following | Rejected |
| Mistral 7B | ~4.0 GB | Would not fit with ML models | Rejected |

Qwen 2.5 also has stronger instruction following than comparably-sized models, which is essential for enforcing our strict no-jargon output format.

---

### Why not fine-tune Qwen on your own data?

Fine-tuning Qwen on our own generated explanations would be circular — we would be training a model to reproduce its own outputs. This causes model collapse: the fine-tuned version loses diversity and gradually degrades in quality.

The correct approach for production is to build a golden dataset: generate 3,000–5,000 explanations, have AML compliance experts manually review and correct each one, then fine-tune on the expert-corrected pairs. This requires domain expertise and time that is out of scope for this project but is explicitly designed for if this were to go to production.

The current prompt engineering approach produces high-quality outputs for a portfolio context and is the right foundation to build the golden dataset from.

---

### Why not SMOTE for class imbalance?

SMOTE generates synthetic samples by interpolating between existing minority class examples in feature space. This works well for continuous features but breaks for our graph-derived features.

A synthetic laundering transaction generated by SMOTE would have a `fan_out_degree` of, say, 12.3 (interpolated between two real examples). But `fan_out_degree` represents a count of real accounts in a real transaction graph — 12.3 is meaningless. Similarly, `is_in_cycle` is a binary flag derived from actual circular edges in the graph. SMOTE cannot synthesise graph relationships.

Using SMOTE would create transactions that look statistically plausible in feature space but represent physically impossible graph structures. This would confuse the model and likely produce overfit behaviour on the synthetic samples.

---

### Why 3-layer imbalance handling?

Each layer addresses a different aspect of the imbalance problem and they compound each other's effect.

**Layer 1 — Undersampling** reduces the training set from 32M to ~387K rows, making GPU training tractable. It also helps the model see fraud cases more frequently during each training epoch. Applied to training set only — the test set retains the original 99.89%/0.11% distribution to give honest evaluation metrics.

**Layer 2 — scale_pos_weight / is_unbalance** tells the model that each fraud case is worth proportionally more in the loss function. This works at the gradient level, complementing the sampling-level change from Layer 1.

**Layer 3 — Threshold tuning** acknowledges that 0.5 is almost never the right threshold for imbalanced data. The optimal threshold is found by scanning the Precision-Recall curve on the validation set and selecting the point that maximises F1. This gave us threshold 0.8514, meaning we only flag transactions where we have very high confidence.

---

### Why threshold 0.8514 and not the default 0.5?

The default threshold of 0.5 would generate an unmanageable number of alerts. On 6.3M test transactions, threshold 0.5 would flag hundreds of thousands of cases — far more than any compliance team can review.

Threshold 0.8514 was selected by maximising F1 score on the validation set Precision-Recall curve. It represents the point where the tradeoff between catching fraud (recall) and not overwhelming investigators (precision) is optimal for this dataset.

At this threshold we catch 81.23% of fraud cases (recall) while keeping alerts to 93,325 out of 6.3M transactions (1.4%). Each alert requires human review, so precision matters operationally even though recall is the primary concern.

---

### Why PySpark for data processing?

The dataset is 31.9 million rows and 2.9 GB as CSV. Pandas would load the entire file into RAM — on most machines this would use 8–12 GB RAM for a single DataFrame operation. More importantly, the graph features (fan-out degree, circular pattern detection, bank-to-bank flow analysis) require operations that are either extremely slow or impossible to express efficiently in Pandas.

PySpark handles the data lazily — operations are only executed when results are needed — and distributes work across cores efficiently. The join operations required for fan-out and fan-in detection across 32M rows would take many minutes in Pandas and are near-instantaneous in Spark.

---

### Why Parquet and not CSV?

Parquet is a columnar storage format. When we read only the columns we need for a particular operation, Parquet only reads those columns from disk — CSV always reads every column. For a dataset with many columns, this is a 3–5x speedup on typical analytical queries.

Parquet also stores schema information (column types) natively. CSV requires type inference on every read, which is slow and can be wrong. Parquet files are also typically 3–4x smaller than equivalent CSV due to column-level compression.

The conversion from CSV to Parquet is a one-time cost that pays for itself within the first few EDA iterations.

---

### Why FastAPI for the backend?

FastAPI is the natural choice for Python ML serving. It is asynchronous (handles concurrent requests without blocking), significantly faster than Flask, auto-generates interactive API documentation via Swagger UI at `/docs`, and has first-class Pydantic integration for request/response validation.

Flask is synchronous — in a multi-user scenario each request blocks the server. Django is too heavy for a pure API backend with no database ORM requirements. Node/Express would require the ML models to be called as a subprocess rather than loaded directly in the same process, adding latency and complexity.

---

### Why React for the frontend?

The dashboard has three distinct interactive tabs with different state requirements — a compliance report viewer with filtering and selection, a live transaction analyser with form state and result display, and a model performance view with visualisations. Managing this complexity in vanilla JavaScript or jQuery would require significant boilerplate.

React's component model keeps the SHAP bar chart, score gauge, explanation formatter, and metric cards isolated and reusable. State management with `useState` is straightforward for this scope. The component-based approach also makes it trivial to later replace the mock scoring logic with real API calls.

---

### How did you prevent data leakage?

Data leakage is the most common error in fraud detection projects and produces inflated metrics that evaporate in production.

Our three main leakage risks were:

**bank_risk_score** — computed as the historical laundering rate per bank. If we compute this across the full dataset, the test set transactions contribute to the score of banks that appear in both sets. Fix: compute bank_risk_score from training set transactions only, then apply the lookup table to the test set.

**fan_out_degree and fan_in_degree** — computed as the number of unique counterparties per account across all transactions. If an account appears in both train and test, its degree computed on the full dataset is inflated by test-set transactions. Fix: compute degree features from training set transactions only.

**is_hub_bank** — hub banks identified from the full dataset. Fix: identify hub banks from training set only.

The general rule: any aggregate feature that uses counts, rates, or labels from the full dataset must be recomputed using only the training partition before being applied to the test partition.

---

### Why 18 features specifically?

The 18 features were selected through the EDA process — each one corresponds to a signal that showed a statistically meaningful difference in laundering rate between positive and negative classes.

We did not include features that showed no signal (currency mismatch had 0% laundering rate — launderers deliberately avoid it), features that would create leakage (raw bank IDs), or features that could not be computed at inference time for a new transaction (features requiring full-dataset graph traversal).

The 18 features split into two categories:

**Transactional (10):** payment_format_risk, amount_log, currency_risk_score, is_cross_border, is_near_threshold, amount_zscore_per_bank, bank_risk_score, hour_of_day, day_of_week, is_weekend

**Graph/Network (8):** is_in_cycle, fan_out_degree, fan_in_degree, tx_velocity, amount_per_tx, is_hub_bank, is_high_fan_out, is_peak_hour

---

### What is the circular transaction pattern and why is it so strong?

A circular transaction (A → B → A) is where account A sends money to account B, and account B sends money back to account A. In legitimate finance this is extremely rare — why would you send money to someone and have them immediately return it?

In money laundering it is a core technique called **layering** — creating the appearance of legitimate transactions to obscure the origin of funds. The money moves through intermediaries to create a paper trail that looks like normal commercial activity.

Our EDA found that circular transactions have a laundering rate of 17.267% — compared to the overall rate of 0.11%. That is a 154x lift. It is by far the strongest single signal in the entire dataset.

The SHAP analysis confirmed this — `is_in_cycle` is consistently one of the top two SHAP drivers for high-scoring transactions.

---

### Why does the model miss some fraud cases?

The false negatives in our case studies reveal a specific and explainable blind spot: accounts with extremely high transaction velocity.

When an account has 48,000+ lifetime transactions, the model has learned from the training data that high-volume accounts are predominantly legitimate (payment processors, market makers, large corporates). This creates a large negative SHAP contribution from `tx_velocity` that can overwhelm positive contributions from other signals like fan-out degree.

The result is that large-scale smurfing operations — accounts distributing funds to thousands of recipients across hundreds of thousands of transactions — can score below the threshold because their sheer volume pattern-matches to legitimate high-volume institutions.

The recommended fix for production is a hard rule: any account with fan_out_degree > 500 and tx_velocity > 10,000 should be escalated for manual review regardless of the ensemble score. Rule-based overrides are appropriate for the specific failure modes of any ML model.

---

### What would you do differently in production?

**Model:** Replace static graph features with a live GNN that traverses the transaction graph at inference time. This would capture dynamic patterns that our static features miss, particularly multi-hop laundering chains (A → B → C → A).

**XAI:** Build the golden dataset — have AML compliance experts review and correct 3,000–5,000 Qwen explanations, then fine-tune on the corrected pairs using QLoRA. This would reduce prompt length from ~800 tokens to ~150 tokens (3–4x inference speedup) and eliminate residual hallucination risk.

**Infrastructure:** Deploy on a split architecture — ML models on a t3.medium (~$30/month) and Qwen on a g4dn.xlarge spun up on-demand (~$0.53/hour only when used).

**Monitoring:** Implement feature drift detection — track the distribution of each of the 18 features over time. When the distribution shifts significantly (launderers adapt their behaviour), retrain the model on recent data.

**Compliance:** Add a full audit trail — every flag, every SHAP value, and every Qwen explanation logged to a tamper-proof store. Regulators require this.

---

## Model Performance

| Metric | Value |
|---|---|
| AUC-ROC | 0.9857 |
| AUC-PR | 0.3857 |
| Recall | 81.23% |
| Precision | 6.00% |
| F1 Score | 0.1117 |
| Threshold | 0.8514 |
| Total test transactions | 6,380,255 |
| Alerts generated | 93,325 (1.46%) |
| True positives | 5,599 |
| False positives | 87,726 |
| False negatives | 1,294 |
| True negatives | 6,285,636 |

**On precision:** 6% precision means 1 in 17 alerts is real fraud. This sounds low but is within the normal range for AML systems in practice — financial crime compliance teams typically see 2–5% precision (95%+ false positive rates) in deployed production systems. Our 6% is above industry average.

---

## Key EDA Findings

| Finding | Signal Strength |
|---|---|
| Circular transactions (A→B→A) | 17.267% laundering rate — **154x baseline** |
| Cross-border transactions | 0.120% vs 0.012% — **10x higher** |
| Weekends | 0.277% vs 0.124% — **2x higher** |
| $8K–$10K amount range | 0.317% vs 0.106% — **3x higher** |
| ACH payment format | 0.795% vs 0.015–0.035% — **40x vs card/crypto** |
| UK Pound / Ruble currency | Highest laundering rate across currencies |
| Currency mismatch | 0.000% — launderers deliberately avoid mismatches |
| Bank 0272142 | $3.88B in self-cycling transactions — major hub |

---

## Feature Engineering

All 18 features were derived from EDA signals. Key design decisions:

**amount_log** — log transformation of transaction amount. Raw amounts span $0 to $8 trillion — this extreme range would dominate gradient calculations. Log transformation compresses the range while preserving the signal (larger amounts = higher risk).

**bank_risk_score** — rolling historical laundering rate per bank, computed on training data only. This encodes institutional risk without using bank IDs directly (which would not generalise to unseen banks).

**is_in_cycle** — binary flag for circular transaction pattern. Requires a two-step graph join: identify all (sender, receiver) pairs, then self-join to find pairs where the reverse also exists. Most impactful single feature in the model.

**amount_zscore_per_bank** — how many standard deviations above the mean this transaction amount is for this specific bank. A $500K transaction is normal for an investment bank but highly unusual for a retail branch.

**is_near_threshold** — binary flag for amounts between $8,000 and $9,999. Captures structuring behaviour without needing to know the exact amount.

---

## XAI Design — Plain English Explanations

The Qwen explanation pipeline has a deliberate translation layer between the ML output and the language model:

```
SHAP values + feature names (ML output)
        ↓
_translate_features() — converts everything to plain English
        ↓
Qwen receives only plain English facts + plain English reasons
        ↓
Qwen writes a compliance report — no technical terms in output
```

This design prevents Qwen from ever seeing terms like `fan_out_degree`, `SHAP=+2.68`, or `payment_format_risk=3`. The output is written for compliance officers, not data scientists.

Each explanation follows a four-section structure that mirrors real AML compliance report templates:

- **ALERT STATUS** — verdict and confidence in one sentence
- **CURRENCY NOTE** — original currency amount and USD equivalent (with approximate FX rate and disclaimer)
- **PRIMARY CONCERN** — the single most important risk signal in plain English
- **SUPPORTING EVIDENCE** — two sentences referencing specific transaction facts
- **INVESTIGATOR NOTE** — actionable next steps specific to this transaction

A post-processing validator checks every output for technical term leakage, hallucinated amounts, and logical contradictions with the actual feature values before returning to the user.

---

## Known Limitations

**Static graph features** — `is_in_cycle` and `fan_out_degree` are computed at training time and approximated at inference time. A live system would need real-time graph traversal.

**High-velocity blind spot** — accounts with extremely high transaction counts can score below threshold even with strong fan-out signals. A rule-based override is recommended for accounts with fan_out > 500 and tx_velocity > 10,000.

**Approximate FX rates** — currency conversion uses hardcoded approximate rates from February 2026. A production system would use a live FX API or the rate recorded at transaction time.

**bank_risk_score leakage** — a 0.62% leakage was identified in audit. The bank risk score computed on training data slightly influences test set performance because some banks appear in both partitions. Impact is minimal but would be eliminated in production by using only pre-cutoff data for bank risk computation.

**Qwen hallucination** — the 1.5B parameter model occasionally generates plausible-sounding but incorrect reasoning. The post-processing validator catches the most common failure modes. A fine-tuned model on expert-reviewed golden cases would eliminate this in production.

---

## Environment

| Component | Version |
|---|---|
| Python | 3.12.2 |
| PyTorch | 2.5.1 (CUDA 12.1) |
| XGBoost | 3.2.0 |
| LightGBM | 4.6.0 |
| SHAP | 0.46.0 |
| Transformers | 4.46.0 |
| PySpark | 4.1.1 |
| FastAPI | 0.115.0 |
| React | 18.x |
| GPU | NVIDIA RTX 3050 Laptop (4.29 GB VRAM) |
| CUDA | 12.1 |
| Java | OpenJDK 17 (required for PySpark 4.x) |

---

*Built by Vatsal — February 2026*
