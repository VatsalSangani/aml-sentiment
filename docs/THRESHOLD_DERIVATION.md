# AML Sentinel — Decision Threshold Derivation

This document explains where the classification threshold (`0.8514`) comes from, why it was chosen, and how to re-derive it if the objective changes. It is the reference pointed to by comments in `model_service.py` and `xai_service.py`.

## What the threshold does

The ensemble (weighted XGBoost + LightGBM) outputs a probability score in [0, 1] for each transaction. The threshold is the cutoff above which a transaction is labelled `FLAGGED`:

```
score >= threshold  →  FLAGGED
score <  threshold  →  CLEARED
```

The default of 0.5 is almost always wrong for highly imbalanced data (here positives are ~0.1% of transactions), so the threshold is tuned.

## How 0.8514 was derived

Computed in `scripts/model_training.ipynb`. The method:

1. Run the trained ensemble on the **validation set** (never the test set — that would be data leakage).
2. Sweep all candidate thresholds with scikit-learn's `precision_recall_curve`.
3. Compute the F1 score at each threshold.
4. Select the threshold that maximises F1.

```python
precision_vals, recall_vals, thresholds = precision_recall_curve(y_val, ens_val)
f1_scores = 2 * precision_vals * recall_vals / (precision_vals + recall_vals + 1e-8)
best_idx = f1_scores.argmax()
best_threshold = thresholds[best_idx]   # → 0.8514, validation F1 = 0.8306
```

The chosen threshold (0.8514) and the ensemble weights are persisted to `models/ensemble_weights.json`, which `model_service.py` loads at runtime.

## Important: validation vs test performance

The threshold was selected on the validation set, where it produced F1 = 0.8306. On the **held-out test set**, the same threshold produced markedly lower performance:

| Threshold | Dataset | F1 | Notes |
|---|---|---|---|
| 0.8514 | validation | 0.8306 | The value chosen and deployed |
| 0.8514 | test | 0.1117 | Held-out performance (what `config.py` reports) |
| 0.9925 | test | 0.3980 | F1-optimal *on test* — NOT used (would be leakage) |

The drop from 0.83 to 0.11 reflects how difficult threshold transfer is under extreme class imbalance (~0.1% positive rate): the validation set's distribution did not fully represent the test set. This is the underlying reason the deployed model shows high recall (0.8123) but low precision (0.0600).

We deliberately kept the validation-derived threshold rather than re-tuning on the test set. Re-tuning on test would inflate reported metrics by leaking test information into a model decision, which is not a defensible practice.

## Why F1 may not be the ideal objective for AML

F1 weights precision and recall equally. In an anti-money-laundering context this is debatable: a missed laundering transaction (false negative) typically carries far higher regulatory and financial cost than a false positive that an analyst reviews and dismisses. A future iteration could therefore tune for a recall-oriented objective instead.

## How to re-derive the threshold for a different objective

Re-run the sweep on the **validation set** (not test) and change only the selection criterion:

- **Optimise F2 (weights recall 2x):**
  ```python
  beta = 2
  f2 = (1 + beta**2) * precision_vals * recall_vals / (beta**2 * precision_vals + recall_vals + 1e-8)
  best_idx = f2.argmax()
  ```

- **Maximise recall subject to a precision floor (e.g. precision >= 0.10):**
  ```python
  mask = precision_vals >= 0.10
  best_idx = recall_vals[mask].argmax()   # map index back to thresholds[mask]
  ```

After re-deriving:

1. Update the `threshold` value in `models/ensemble_weights.json`.
2. Update `XAI_THRESHOLD` in `backend/services/xai_service.py` to match — these are currently two separate copies and must be kept in sync (or refactor the XAI service to read the same JSON).
3. Re-record the resulting validation and test metrics in `config.py` and `README.md`.

## Source of truth

- Deployed threshold: `models/ensemble_weights.json` → `threshold`
- Derivation code: `scripts/model_training.ipynb`
- Reported metrics: `config.py` (`MODEL_*` constants) and `README.md`
