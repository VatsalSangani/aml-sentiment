# AML Sentinel — Model Training Notes
> Purpose: Detailed explanation of training approach, techniques, and data challenges
> Author: Vatsal
> Last Updated: February 20, 2026

---

## 🎯 WHY XGBoost + LightGBM ENSEMBLE?

### Why Not Other Models?
- **Random Forest** — Cannot handle 32M rows efficiently, no GPU support, too slow
- **Deep Learning (MLP)** — Black box, hard to explain to regulators, overkill for tabular data
- **GNN (Graph Neural Network)** — Best for pure graph problems but requires significant VRAM, complex setup, risky on 4.29GB
- **Logistic Regression** — Too simple, cannot capture non-linear fraud patterns

### Why XGBoost?
- Native GPU support (`device=cuda`) — critical for our 4.29GB VRAM constraint
- `scale_pos_weight` parameter specifically designed for imbalanced classification
- Handles missing values natively
- Built-in feature importance — complements Qwen XAI explanations
- Industry standard for fraud detection at financial institutions
- Excellent on tabular data with mixed feature types

### Why LightGBM?
- Faster training than XGBoost on large datasets (32M rows)
- Lower memory footprint — important for our VRAM constraint
- `is_unbalance` and `class_weight` parameters for imbalance
- Leaf-wise tree growth catches subtle fraud patterns XGBoost might miss
- Different internal algorithm = catches different patterns

### Why Ensemble?
- XGBoost and LightGBM make errors on different samples
- Weighted average of their probabilities reduces variance
- In fraud detection, ensemble models consistently outperform single models
- If one model misses a laundering pattern, the other may catch it

---

## 🔀 TRAIN/TEST SPLIT STRATEGY

### Why Temporal Split Instead of Random Split?
A random split would be **data leakage** in disguise for time-series financial data:
- Random split lets the model "see the future" during training
- In real deployment, the model will only ever see past transactions
- Temporal split simulates real-world deployment accurately

### Our Approach:
```
Training Set  → Earlier dates (80% of time range)
Test Set      → Later dates  (20% of time range)
```

### Why This Matters:
- Prevents inflated evaluation metrics
- Tests whether the model generalises to unseen time periods
- Regulators require models to be validated on out-of-time samples
- More honest representation of real-world performance

---

## ⚖️ CLASS IMBALANCE HANDLING

### The Problem:
```
Legitimate   : 31,863,008  (99.89%)
Laundering   :     35,230  (0.11%)
Ratio        : ~904:1
```
A naive model predicting "all legitimate" achieves 99.89% accuracy — completely useless.

### Our 3-Layer Strategy:

**Layer 1: Undersampling**
- Keep ALL 35,230 laundering transactions
- Randomly sample 352,300 legitimate transactions (10:1 ratio)
- Total training data: ~387,530 rows
- Why: Reduces memory pressure on 4.29GB VRAM, speeds up training
- Why 10:1: Aggressive enough to help the model, conservative enough to preserve patterns
- Applied to TRAINING SET ONLY — test set remains original distribution

**Layer 2: scale_pos_weight / is_unbalance**
- XGBoost: `scale_pos_weight = legitimate_count / laundering_count`
- LightGBM: `is_unbalance = True`
- Computed from TRAINING SET only (not full dataset) to prevent leakage
- Tells the model that each laundering transaction is worth more
- Works alongside undersampling for double protection

**Layer 3: Threshold Tuning**
- Default classification threshold is 0.5
- For imbalanced data, 0.5 is almost always wrong
- We find the optimal threshold using Precision-Recall curve on validation set
- Optimise for F1 score on the validation set
- Apply tuned threshold to test set predictions

### Why NOT SMOTE?
- SMOTE generates synthetic laundering transactions
- Problem: Our graph features (is_in_cycle, fan_out_degree) cannot be meaningfully synthesised
- A synthetic transaction doesn't have real graph relationships
- Risk of creating unrealistic patterns that confuse the model
- Memory intensive on 32M rows

---

## 🚨 DATA LEAKAGE PREVENTION

### What is Data Leakage?
When information from the test set (future) leaks into training, creating artificially inflated metrics that don't reflect real performance.

### Leakage Risks in Our Dataset:

**Risk 1: bank_risk_score**
- Computed as laundering rate per bank across ALL transactions
- If test set transactions influence this score, the model "knows the future"
- **Fix:** Compute bank_risk_score using ONLY training set transactions, then apply to test set

**Risk 2: fan_out_degree / fan_in_degree**
- Computed across all transactions for each account
- Test set transactions inflate these counts
- **Fix:** Compute degree features from training set only

**Risk 3: is_hub_bank**
- Hub banks identified from full dataset
- **Fix:** Identify hub banks from training set only

### Rule of Thumb:
> Any aggregate feature that uses labels or counts from the full dataset must be recomputed on training data only.

---

## 🧹 NULL / MISSING VALUE HANDLING

### Why Nulls Exist:
- `fan_in_degree` — accounts that only send, never receive → null after left join
- `fan_out_degree` — accounts that only receive, never send → null after left join
- `amount_zscore_per_bank` — banks with single transaction have null std dev
- `bank_risk_score` — new banks not seen in training set

### Our Strategy:
| Feature | Null Fill Strategy | Reason |
|---------|-------------------|--------|
| fan_in_degree | 0 | Account has no incoming connections |
| fan_out_degree | 0 | Account has no outgoing connections |
| fan_in_degree | 0 | No connections = not a hub |
| amount_zscore_per_bank | 0 | Treat as average if no bank history |
| bank_risk_score | 0 | Unknown bank = assume no risk history |
| tx_velocity | 1 | At least 1 transaction exists |

### XGBoost vs LightGBM Null Handling:
- XGBoost: Handles nulls natively by learning which direction to split
- LightGBM: Also handles nulls but explicit filling is safer and more predictable

---

## 📊 EVALUATION METRICS

### Why NOT Accuracy?
```
Naive model accuracy = 99.89% (predicts all legitimate)
Our model accuracy   = ~99.90% (catches some fraud)
Difference           = 0.01% ← meaningless
```

### Metrics We Use and Why:

**Primary Metric: AUC-PR (Area Under Precision-Recall Curve)**
- Best metric for severely imbalanced datasets
- Focuses on the minority class (fraud)
- Not influenced by the large number of true negatives
- Score of 1.0 = perfect, 0.11 = random (baseline = class prevalence)

**Secondary Metrics:**
| Metric | Formula | Why Important |
|--------|---------|--------------|
| Recall | TP / (TP + FN) | Fraction of fraud cases caught — highest priority |
| Precision | TP / (TP + FP) | Fraction of flagged cases that are real fraud |
| F1 Score | 2×P×R / (P+R) | Balance of precision and recall |
| Confusion Matrix | — | Visual breakdown of all prediction types |

### Priority Order for AML:
```
1. Recall    → Missing fraud = criminal goes free (highest cost)
2. Precision → False alarm = analyst wastes time (lower cost)
3. F1        → Overall balance
4. AUC-PR    → Model quality independent of threshold
```

---

## 🛑 EARLY STOPPING

### Why Early Stopping?
- Without it, models overfit to training data
- Overfitting is especially dangerous with imbalanced data
- Model memorises the rare fraud cases instead of learning patterns

### Our Approach:
- Hold out 20% of training data as validation set
- Monitor AUC-PR on validation set after each round
- Stop training if no improvement for 50 consecutive rounds
- Restore best model weights from the optimal round

---

## 💾 MEMORY MANAGEMENT

### The Challenge:
- 32M rows × 18 features = ~4.6GB as float32
- Our GPU has exactly 4.29GB VRAM
- Loading everything at once will cause OOM (Out of Memory) error

### Our Strategy:
```
Spark DataFrame (distributed, lazy)
        ↓
Apply undersampling (reduce to ~387K rows)
        ↓
Convert to Pandas (fits in RAM easily now)
        ↓
Convert to NumPy arrays
        ↓
XGBoost DMatrix / LightGBM Dataset (GPU optimised)
```

### Why This Works:
- After undersampling we have ~387K rows not 32M
- This fits comfortably in both RAM and VRAM
- Spark handles the heavy lifting of filtering and sampling
- GPU only ever sees the manageable undersampled dataset

---

## 🔧 HYPERPARAMETERS

### XGBoost Key Parameters:
| Parameter | Value | Reason |
|-----------|-------|--------|
| device | cuda | GPU acceleration |
| tree_method | hist | Fastest GPU method |
| max_depth | 6 | Prevent overfitting |
| learning_rate | 0.05 | Slow learning = better generalisation |
| n_estimators | 1000 | High but early stopping controls actual count |
| scale_pos_weight | ~904 | Computed from training set ratio |
| eval_metric | aucpr | Our primary metric |
| early_stopping_rounds | 50 | Stop if no improvement |

### LightGBM Key Parameters:
| Parameter | Value | Reason |
|-----------|-------|--------|
| device | gpu | GPU acceleration |
| num_leaves | 31 | Controls tree complexity |
| learning_rate | 0.05 | Matches XGBoost for fair comparison |
| n_estimators | 1000 | High but early stopping controls actual count |
| is_unbalance | True | Handles class imbalance |
| metric | average_precision | Our primary metric |
| early_stopping_rounds | 50 | Stop if no improvement |

---

## 🎯 ENSEMBLE STRATEGY

### Weighted Average:
```python
final_prob = (0.5 × xgb_prob) + (0.5 × lgb_prob)
```

### Why Equal Weights Initially?
- We don't know which model is better until we evaluate
- After seeing validation AUC-PR we can adjust weights
- If XGBoost AUC-PR = 0.85 and LightGBM = 0.80:
  - Adjusted: 0.6 × xgb + 0.4 × lgb

---

## ⚠️ POTENTIAL ISSUES & MITIGATIONS

| Issue | Likelihood | Impact | Mitigation |
|-------|-----------|--------|-----------|
| OOM on GPU | Medium | High | Undersample before GPU training |
| Data leakage | High without care | High | Recompute aggregates on train only |
| Overfitting to fraud | Medium | Medium | Early stopping + validation set |
| Poor recall | Medium | High | scale_pos_weight + threshold tuning |
| Slow training | Low | Low | GPU acceleration handles this |
| Null values crashing | Low | Medium | Explicit null filling before training |
| Wrong threshold | High | High | Tune on validation Precision-Recall curve |

---

## 📁 OUTPUT FILES
After training we will save:
- `models/xgb_model.json` — XGBoost model
- `models/lgb_model.txt` — LightGBM model
- `models/feature_importance.csv` — Feature rankings
- `models/threshold.txt` — Optimal decision threshold
- `models/evaluation_report.txt` — Full metrics report