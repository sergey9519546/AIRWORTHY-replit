# Model Audit — Rentalizer Revenue Prediction

**Auditor:** Senior ML Engineer
**Date:** 2026-06-29
**Model:** XGBoost v1.0.0, R² = 0.9974, MAPE = 2.0%

---

## Executive Summary

**This model is fundamentally broken.** The reported R² of 0.997 and MAPE of 2.0% are artifacts of severe feature leakage, not genuine predictive power. The single most important feature (`reviews_ltm`, 60.2% importance) is a direct proxy for the target variable. The model is essentially learning "listings that had more bookings last year earned more revenue last year" — a tautology, not a prediction.

In production, this model will **dramatically underperform** its reported metrics. The inference pipeline already contains a band-aid heuristic to compensate, which itself introduces untested assumptions.

---

## 1. Feature Leakage — P0 CRITICAL

### The Smoking Gun

| Feature | Importance | Why It Leaks |
|---------|-----------|--------------|
| `reviews_ltm` | **60.2%** | Reviews in last 12 months are a direct consequence of bookings. Target is `estimated_revenue_l365d`. More bookings → more reviews → more revenue. Circular. |
| `reviews_per_month_num` | 1.7% | Same issue — review velocity is a proxy for booking frequency. |
| `reviews_total` | 1.0% | Lifetime review count correlates with lifetime revenue. |
| `review_recency_days` | 0.8% | Recent reviews = recent bookings = recent revenue. |
| `reviews_ltm_ratio` | 0.7% | Derived from `reviews_ltm`. Inherits the leak. |
| `availability_365_num` | 0.6% | Low availability = high occupancy = high revenue. Post-outcome. |
| `availability_30_num` | ~0.1% | Same issue at shorter window. |

**Total importance of leaky features: ~65%**

### Mechanism

The target `estimated_revenue_l365d` is Airbnb's own revenue estimate for the trailing 365 days. The features `reviews_ltm`, `reviews_per_month_num`, and `availability_*` are measured over the same or overlapping time windows. The model isn't predicting future revenue from listing characteristics — it's reconstructing past revenue from its direct consequences.

### What a Non-Leaky Model Looks Like

If you remove all review/availability features and retrain, expect R² to drop from 0.997 to **0.3–0.5** range. That's the model's true predictive power from listing characteristics alone (location, size, price, host attributes).

**Verdict: P0 — Must fix before any production deployment.**

---

## 2. Overfitting — P0 (Secondary to Leakage)

### Why R² = 0.997 Is Not Real

The suspiciously high R² is entirely explained by leakage. With `reviews_ltm` carrying 60% importance and being a near-perfect proxy for the target, the model is doing regression on a feature that's ~90% correlated with the target. This isn't overfitting in the traditional sense (memorizing noise) — it's learning a deterministic relationship that won't exist at inference time.

### Evidence from Inference Pipeline

In `features.py`, during inference, ALL review features are hardcoded to 0:
```python
features["reviews_ltm"] = 0
features["reviews_per_month_num"] = 0
features["reviews_total"] = 0
```

This means the model's most important feature (60.2% importance) is **always zero at prediction time**. The model trained on rich review signals but predicts on zeros. This is catastrophic.

### The Band-Aid in api.py

The API contains a heuristic blend (lines in `api.py`) that detects when model predictions are "way too low" compared to comp median and overrides with comp-based predictions:

```python
if model_revenue < comp_median * 0.3:
    alpha = 0.2  # 20% model, 80% comp
elif model_revenue < comp_median * 0.6:
    alpha = 0.5
```

This is an admission that the model doesn't work for new listings. The blend logic in `api.py` is different from the blend in `train_model.py` — the training blend achieved α=1.0 (pure XGBoost), but production uses ad-hoc overrides.

**Verdict: P0 — The reported metrics are meaningless for production performance.**

---

## 3. Generalization — P0

### Will This Work on New Data?

**No.** Several fundamental generalization failures:

1. **Temporal leakage**: All data is from a single scrape window (2026-06-14). No temporal train/test split. The model hasn't been tested on future data. Revenue patterns shift seasonally (summer in NYC vs. winter), and the model has zero ability to capture this.

2. **Geographic limitation**: NYC only. The model encodes borough as one-hot. Applying this to other cities would require retraining. Even within NYC, neighborhoods vary dramatically.

3. **New listing problem**: A brand-new listing has no reviews, no availability history, no review score. The model receives zeros for 65% of its predictive power. It will default to a baseline prediction based on price/bedrooms alone.

4. **Market regime changes**: Post-COVID, regulatory changes (NYC Local Law 18), seasonal shifts — none of these are captured. The model is a snapshot, not a living predictor.

5. **Selection bias**: The model is trained only on listings with `estimated_revenue_l365d > 0`. Failed or delisted listings are excluded. This creates survivorship bias — the model learns from winners only.

**Verdict: P0 — Model will degrade significantly on any out-of-distribution input.**

---

## 4. Feature Engineering — P1

### What's Good
- Price per person (derived) is reasonable
- Borough and property type one-hot encoding is appropriate
- Log-transform of target is correct for revenue data
- Outlier removal at 1st/99th percentile is sensible

### What's Missing

| Missing Feature | Expected Impact | Notes |
|----------------|----------------|-------|
| **Day-of-week / seasonal patterns** | High | NYC revenue is highly seasonal. No month/season features. |
| **Distance to subway** | High | Transit access is a top driver of NYC STR demand. |
| **Distance to tourist attractions** | Medium | Times Square, Central Park, etc. |
| **Neighborhood income/demographics** | Medium | Census data would add signal. |
| **Listing photos quality score** | Medium | Photo count/quality drives bookings. |
| **Host response rate/time** | Medium | Available in source data, not used. |
| **Cancellation policy** | Low-Medium | Affects booking conversion. |
| **Number of amenities** | Medium | Pool, gym, view, etc. |
| **Floor level** | Low | High-floor apartments command premium. |
| **Building age/type** | Low | Pre-war vs. new construction. |

### What's Wrong

- **`occupancy_proxy`**: Computed as `(365 - availability_365) / 365`. This is the same leakage as availability_365, just rescaled.
- **`beds_num`**: Estimated as `accommodates // 2` when missing. This is a rough heuristic, not real data.
- **`listing_age_months`**: Uses `first_review` as proxy. Many listings exist before their first review. Should use `host_since` or listing creation date.
- **Property type defaults**: In inference, all listings default to "Entire rental unit" regardless of actual type. This silently misclassifies condos, townhouses, etc.

**Verdict: P1 — Feature engineering is functional but has critical gaps and leakage.**

---

## 5. Model Selection — P2

### Is XGBoost the Right Choice?

**Partially.** XGBoost is a reasonable default for tabular data, but:

1. **No deep learning baseline**: For a production system predicting revenue, a neural network with embeddings for categorical variables (borough, property type) might capture interactions better.

2. **No linear model comparison**: Ridge baseline exists in the code but metrics aren't saved or compared properly. If Ridge with non-leaky features performs within 10% of XGBoost, the simpler model is preferable for production.

3. **LightGBM trained but ignored**: LightGBM is trained but never used in the blend or saved. This is wasted compute. Either use it or don't train it.

4. **CatBoost mentioned but absent**: The script header mentions CatBoost but it's never implemented.

5. **No ensemble of diverse models**: The blend is XGBoost + comp-based median. A proper ensemble would blend XGBoost, LightGBM, and Ridge for diversity.

**Verdict: P2 — Model choice is acceptable but not optimal. The leakage issue dwarfs model selection concerns.**

---

## 6. Hyperparameter Tuning — P1

### Optuna Configuration Issues

1. **Evaluating on leaked data**: Optuna's cross-validation uses the same leaked features. The "best" hyperparameters are optimized for a meaningless objective. Tuning is garbage-in-garbage-out.

2. **Only 20 trials by default**: For 8 hyperparameters, 20 trials is insufficient. The search space is:
   - max_depth: 3–8 (6 values)
   - learning_rate: 0.01–0.3 (continuous, log)
   - n_estimators: 100–800 (701 values)
   - min_child_weight: 1–10 (10 values)
   - subsample: 0.6–1.0 (continuous)
   - colsample_bytree: 0.6–1.0 (continuous)
   - reg_alpha: 1e-8–10.0 (continuous, log)
   - reg_lambda: 1e-8–10.0 (continuous, log)

   With 20 trials, Optuna barely scratches the surface. Should be 100–200 minimum.

3. **Regularization is near-zero**: `reg_alpha = 1.74e-8`, `reg_lambda = 1.02e-8`. These are effectively zero. The model has no regularization, which means it can overfit freely to the leaked features.

4. **Early stopping split is naive**: The 80/20 split for early stopping is sequential (first 80% train, last 20% val). If data is ordered by any pattern, this creates bias. Should use a random split or temporal split.

5. **Cross-validation in Optuna vs. final model**: Optuna uses 5-fold CV on the full training set. The final model trains on 80% with early stopping on 20%. These are different evaluation protocols, so the "best" parameters from Optuna may not be optimal for the final model.

**Verdict: P1 — Tuning methodology has issues, but fixing leakage is more urgent.**

---

## 7. Evaluation — P1

### Metrics Used
- MAE, RMSE, R², MAPE, MdAPE, Within-25%, Within-50%

### What's Missing

1. **No stratified evaluation**: Metrics are computed globally. Should break down by:
   - Borough (Manhattan vs. Bronx have very different revenue distributions)
   - Price tier (cheap vs. luxury)
   - Listing type (studio vs. 3BR)
   - Review count (experienced vs. new hosts)

2. **No confidence intervals on metrics**: A single R² number without CI is uninformative. With 1,023 test samples, bootstrap CIs would show the true uncertainty.

3. **MAPE is misleading**: With a minimum revenue of ~$4,300 and max of ~$275K, MAPE treats a $500 error on a $5K listing the same as a $5K error on a $50K listing. MdAPE (0.8%) is more robust but still doesn't capture the distribution.

4. **No business-relevant metrics**: For a revenue prediction tool, what matters is:
   - What % of predictions are within $X of truth?
   - What's the worst-case error for the 90th percentile?
   - How does error vary by listing price?

5. **Test set is from the same distribution**: Random train/test split from the same scrape means the test set has the same leakage. The metrics are inflated.

**Verdict: P1 — Metrics are technically correct but meaningless due to leakage. Need stratified, temporal evaluation.**

---

## 8. Confidence Intervals — P2

### Methodology

The `confidence.py` computes CIs from comp listing revenues:
- Uses 10th/90th percentile of comp revenues
- Blends with prediction via `min(p10, pred*0.7)` and `max(p90, pred*1.3)`
- Classifies as high/medium/low based on coefficient of variation

### Issues

1. **CI is based on comps, not model uncertainty**: The confidence interval reflects how similar nearby listings are, not how uncertain the model is. A model prediction of $100K with comps averaging $30K would get a CI that doesn't include the model's own prediction.

2. **No prediction interval from the model**: XGBoost can generate prediction intervals via quantile regression or conformal prediction. This isn't used.

3. **Asymmetric bounds are arbitrary**: `revenue_lower = min(p10, pred*0.7)` and `revenue_upper = max(p90, pred*1.3)` are magic numbers. Why 0.7x and 1.3x? Why not 0.5x and 2x?

4. **Downgrade logic is conservative**: `n_comps < 5 → low`, `n_comps < 10 and high → medium`. This means most predictions will be "low" confidence since finding 10+ similar listings is rare.

5. **No calibration**: The CIs aren't tested for calibration. A "high" confidence 80% CI should contain the true value 80% of the time. This isn't verified.

**Verdict: P2 — CI methodology is reasonable for a v1 but needs calibration testing.**

---

## 9. Blend Logic — P1

### Training Blend vs. Production Blend

**Training** (`train_model.py`):
- Grid searches α from 0 to 1 in 0.05 steps
- Optimizes for MAPE on test set
- Result: α = 1.0 (pure XGBoost, no comp blending)

**Production** (`api.py`):
- Uses ad-hoc heuristics based on model vs. comp median ratio
- α = 0.2, 0.5, 0.7, or 0.9 depending on the gap
- This is completely different from the training blend

### The Problem

The training blend found that α=1.0 (pure XGBoost) is optimal. This is because XGBoost has access to leaked review features during training, so it outperforms comps. But at inference time, review features are zero, so XGBoost underperforms. The production code patches this with heuristics.

This means:
1. The blend was optimized on leaked data → wrong α
2. Production uses a different blend than training → no optimization
3. The heuristics in api.py are untested and unvalidated

### What Should Happen

Either:
- **Remove leaky features** and re-optimize the blend (likely α ≈ 0.3–0.5)
- **Use a stacking model** that learns when to trust XGBoost vs. comps
- **Use a single unified model** that includes comp-derived features as inputs

**Verdict: P1 — Blend logic is inconsistent between training and production.**

---

## 10. Production Failure Modes

### What Will Break This Model

| Failure Mode | Severity | Likelihood | Description |
|-------------|----------|------------|-------------|
| **New listing (0 reviews)** | P0 | Certain | Model gets 0 for 60% of its predictive power. Defaults to price/bedrooms only. |
| **Regulatory change** | P0 | High | NYC Local Law 18 (2023) requires host registration. Unregistered listings can't operate. Model doesn't know about this. |
| **Seasonal variation** | P1 | Certain | Model trained on June 2026 data. December revenue is 30-50% lower in NYC. No seasonal adjustment. |
| **Price gaming** | P1 | Medium | Host can set nightly_rate = $5000 to inflate prediction. Model uses price_num as second-most-important feature. |
| **Coordinate spoofing** | P1 | Low | User can provide any NYC coordinates. No verification that the address matches the coordinates. |
| **Data staleness** | P1 | Certain | Model is trained on a single snapshot. Revenue patterns shift over time. No retraining pipeline. |
| **Comp index failure** | P2 | Low | KD-Tree built on training data. If training data is corrupted, comp predictions fail silently. |
| **Geocoding failure** | P2 | Medium | Mapbox geocoding can fail or return wrong location. No fallback geocoder. |
| **Out-of-NYC input** | P2 | Medium | Bounds check exists but borough detection uses crude bounding boxes. Staten Island detection is weak. |
| **Memory pressure** | P2 | Low | KD-Tree + full training data loaded into memory. With 4K listings it's fine, but doesn't scale. |

### Critical Production Gaps

1. **No monitoring**: No tracking of prediction accuracy over time. No drift detection.
2. **No retraining pipeline**: Model is static. No mechanism to retrain with new data.
3. **No A/B testing framework**: Can't compare model versions in production.
4. **No rate limiting**: API has no rate limits. Could be abused.
5. **No caching validation**: 7-day cache TTL means stale predictions for a week.

---

## Summary of Findings

| # | Finding | Severity | Impact |
|---|---------|----------|--------|
| 1 | `reviews_ltm` (60% importance) is a direct proxy for target | **P0** | Model is cheating. Metrics are meaningless. |
| 2 | All review/availability features leak target information | **P0** | ~65% of model power comes from leaky features. |
| 3 | Inference zeros out the most important feature | **P0** | Model dramatically underperforms at prediction time. |
| 4 | Production blend uses untested heuristics, not trained blend | **P1** | Inconsistent behavior between training and serving. |
| 5 | No temporal validation — single snapshot, random split | **P0** | Unknown performance on future data. |
| 6 | Missing critical features (seasonality, transit, amenities) | **P1** | Model can't capture important revenue drivers. |
| 7 | Optuna with only 20 trials and near-zero regularization | **P1** | Insufficient tuning, overfitting to leaked features. |
| 8 | No stratified evaluation by borough/price/listing type | **P1** | Unknown performance across segments. |
| 9 | Confidence intervals not calibrated, based on comps not model | **P2** | CI may not have correct coverage. |
| 10 | No monitoring, retraining, or drift detection | **P1** | Model will degrade silently over time. |
| 11 | Survivorship bias — trained only on profitable listings | **P1** | Model can't predict for underperformers. |
| 12 | Property type defaults to "Entire rental unit" in inference | **P2** | Silent misclassification for non-default types. |

---

## Recommendations

### Immediate (Before Any Deployment)

1. **Remove all leaky features**: Strip `reviews_ltm`, `reviews_per_month_num`, `reviews_total`, `review_recency_days`, `reviews_ltm_ratio`, `availability_365_num`, `availability_30_num`, `occupancy_proxy`.
2. **Retrain and re-evaluate**: Expect R² to drop to 0.3–0.5. That's the real baseline.
3. **Re-optimize blend**: With non-leaky features, the blend will likely favor comps more. Re-run grid search.
4. **Add temporal validation**: Split data by time (e.g., train on Jan-Jun, test on Jul-Dec) to test generalization.

### Short-Term (v2)

5. **Add seasonality features**: Month of year, holiday flags, day-of-week patterns.
6. **Add location features**: Distance to subway, tourist attractions, business districts.
7. **Add host features**: Response rate, response time, acceptance rate.
8. **Increase Optuna trials**: 100–200 minimum.
9. **Implement conformal prediction**: For calibrated confidence intervals.
10. **Stratified evaluation**: Report metrics by borough, price tier, and listing type.

### Long-Term (Production)

11. **Build retraining pipeline**: Automated monthly retraining with new data.
12. **Add monitoring**: Track prediction accuracy, drift, and feature distributions.
13. **Implement A/B testing**: Compare model versions in production.
14. **Add rate limiting and caching**: Protect the API.
15. **Consider a unified model**: Instead of blending XGBoost + comps, use comp statistics as features in a single model.

---

## Bottom Line

**Do not deploy this model.** The R² of 0.997 is a lie. The model is learning from features that won't exist at prediction time. Strip the leaky features, retrain, and you'll see the true performance — likely mediocre, but honest. Then iterate from there.

The infrastructure (API, comp finder, geocoding, UI) is solid. The ML is not.
