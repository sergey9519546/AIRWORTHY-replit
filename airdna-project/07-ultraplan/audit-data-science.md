# Data Science Audit: Rentalizer Clone — Revenue Prediction Engine

**Auditor:** Senior Data Scientist (Subagent)
**Date:** 2026-06-29
**Verdict:** ⚠️ **CONDITIONAL PASS — Several Critical Issues Must Be Addressed**

---

## Executive Summary

The plan is well-structured and the pivot to supervised learning on InsideAirbnb's labeled data is the correct call given the analysis findings. However, there are **3 critical**, **5 significant**, and **4 minor** data science issues that will materially impact model quality if unaddressed.

---

## 1. Feature Engineering — ⚠️ SIGNIFICANT GAPS

### What's Good
- Price, location, reviews, availability — all reasonable starting features
- `price_per_person` and `review_velocity` are sensible derived features
- `occupancy_proxy` is pragmatic given the data

### What's Missing (Critical)

**A. Seasonality / Temporal Features — ABSENT**
The plan completely ignores time. Short-term rental revenue is **heavily seasonal**. A listing in Manhattan in December vs. July can differ by 2-3x. InsideAirbnb's `estimated_revenue_l365d` is an annual aggregate, but:
- You have no way to decompose this into seasonal patterns
- The `monthly_revenue` array in the API response (12 values) is **fabricated** — the model has no monthly data to produce this. This is a hallucination endpoint that will return meaningless numbers unless you either:
  - (a) Train 12 separate monthly models (need monthly labeled data — not available), or
  - (b) Use a seasonal decomposition heuristic (e.g., NYC occupancy curves from public data), or
  - (c) **Remove the monthly breakdown from the API entirely** (recommended for MVP)

**B. Distance to Key Attractions — ABSENT**
For NYC specifically, proximity to Times Square, Central Park, subway stops, airports, convention centers, etc. is a **strong predictor** of STR revenue. The raw lat/lng won't capture this — XGBoost can't learn "Manhattan is near Times Square" from coordinates alone. Suggest:
- Distance to nearest subway station (MTA data is public)
- Distance to Times Square / Central Park / major hubs
- Walk score or transit score (if obtainable)

**C. Neighborhood Quality Proxies — ABSENT**
- Median household income by census tract
- Crime rate by precinct
- Restaurant/bar density (proxy for "vibrancy")

**D. Host Sophistication Features — PARTIALLY ABSENT**
- `host_response_rate` and `host_response_time` — strong signals of professional hosting
- `host_has_profile_pic` — weak but available
- Number of photos / description length — quality proxies (not in the plan)
- Whether the listing has a professional title (regex on capitalization patterns)

**E. Review Recency — ABSENT**
- `last_review` date is available. A listing with its last review 18 months ago is dead. A listing with a review last week is active. This is a stronger signal than `reviews_per_month` which is an average over the listing's lifetime.

### Verdict
The feature set is a reasonable **v1** but is missing several high-signal features. At minimum, add: review recency, subway distance, and kill the monthly_revenue endpoint.

---

## 2. Model Choice — ✅ XGBoost IS APPROPRIATE, but not alone

### Why XGBoost Works Here
- Tabular data with mixed feature types — XGBoost's natural habitat
- Handles non-linear relationships and interactions automatically
- Robust to outliers (with proper tuning)
- Good with ~5K samples if regularized properly
- SHAP integration for interpretability

### Why XGBoost Alone Is Insufficient
The plan proposes a 60/40 XGBoost/comp blend, which is good. But consider:

**A. LightGBM or CatBoost should be baselined**
- CatBoost handles categorical features natively (no encoding needed) — your plan has several categoricals (`borough`, `property_type`, `instant_bookable`, `host_is_superhost`) that will need one-hot encoding with XGBoost, inflating dimensionality
- LightGBM is faster and often outperforms XGBoost on small datasets
- **Recommendation:** Train all three, pick the best on CV. This costs ~30 extra minutes of compute.

**B. A simple k-NN regressor on the comp features should be a baseline**
- The comp finder IS a k-NN regressor. Formalizing it as a baseline model (with the similarity weighting) gives you a clean comparison.
- If XGBoost can't beat the comp-based approach by a meaningful margin, the complexity isn't justified.

**C. Linear models as sanity checks**
- Ridge regression on the same features. If Ridge gets R²=0.65 and XGBoost gets R²=0.72, the marginal gain from non-linearity is small and the interpretability cost is high.

### Verdict
XGBoost is a fine choice. But **train LightGBM and CatBoost alongside it** (trivial extra effort), and include a Ridge baseline. Pick the winner on CV, not by assumption.

---

## 3. Log-Transforming the Target — ✅ CORRECT, with caveats

### Why It's Right
- Revenue distributions are right-skewed (a few high-earners, many low-earners)
- Log transform makes the distribution more Gaussian, which helps tree-based models split more evenly
- MAPE naturally benefits from log-space predictions (symmetric error treatment)
- Prevents the model from being dominated by high-revenue outliers

### Caveats

**A. Inverse Transform Bias**
When you convert predictions back from log-space (`exp(pred)`), you get the **median** of the predicted distribution, not the **mean**. For revenue estimation, you likely want the mean (expected value). Apply **Duan's smearing estimator** or multiply by `exp(σ²/2)` to correct for this bias. Without this, you will **systematically underpredict** revenue by 5-15%.

**B. Zero Revenue Handling**
If any listings have `estimated_revenue_l365d` that rounds to 0 after filtering, `log(0)` = -∞. The plan filters for `> 0`, which is correct, but verify no near-zero values sneak through.

**C. Evaluate in Dollar Space**
All metrics (MAE, MAPE, Within X%) must be computed in **original dollar space**, not log-space. A model that looks great in log-space can look mediocre in dollar space due to the asymmetric error amplification on high-revenue properties.

### Verdict
Log-transform is correct. Add the smearing correction and always evaluate in dollar space.

---

## 4. Evaluation Metrics — ⚠️ GOOD BUT INCOMPLETE

### What's Good
- MAE, MAPE, R², Within 25/50% — solid baseline metric set
- Target thresholds are reasonable

### What's Missing

**A. Median Absolute Percentage Error (MdAPE)**
MAPE is sensitive to outliers (one $500 listing with a $50K prediction tanks it). MdAPE gives the "typical" error. Report both.

**B. Stratified Metrics**
Revenue varies enormously by borough and listing tier. A model that's great on Manhattan but terrible on Staten Island is useless. Report metrics **per borough** and **per revenue tier** (e.g., <$20K, $20-50K, $50-100K, >$100K).

**C. Calibration of Confidence Intervals**
The plan generates confidence intervals but never validates them. You need:
- **Coverage:** What % of true values fall within the predicted CI? (Should be ~80% for an 80% CI)
- **Sharpness:** How wide are the CIs? (Narrower is better, but not at the cost of coverage)
- Without this, the confidence intervals are decorative, not informative.

**D. Residual Analysis**
- Plot residuals vs. predicted values (heteroscedasticity check)
- Plot residuals vs. each feature (systematic bias check)
- QQ plot of residuals (normality check)
- These are more valuable than any single metric.

### Verdict
Add MdAPE, stratified metrics, CI calibration, and residual plots.

---

## 5. Sample Size — ⚠️ TIGHT BUT WORKABLE

### The Math
- ~5,000 samples after filtering
- 80/20 split → 4,000 train / 1,000 test
- 5-fold CV → 3,200 train / 800 validation per fold
- ~20-25 features after encoding

**Rule of thumb:** You need ~10-20 samples per feature for stable tree-based models. With 25 features, you need 250-500 samples minimum. You have 3,200 per fold. **This is fine.**

### The Real Risk
The risk isn't sample size per se — it's **sample representativeness**:
- 5,000 STR listings in NYC is a **thin slice** of the market
- After outlier removal (1st/99th percentile), you may lose 100+ samples
- Boroughs will be imbalanced (Manhattan dominates, Staten Island may have <100 listings)
- Property types will be heavily skewed (mostly apartments)

### Recommendations
- **Stratified sampling by borough** for train/test split (already planned — good)
- **Consider SMOTE or other augmentation** for underrepresented boroughs/property types (probably overkill for v1, but keep in mind)
- **Report per-borough sample counts** in the training set
- **Don't over-filter:** Each additional filter (min_nights, has_availability, etc.) shrinks your dataset. Verify each filter is necessary.

### Verdict
5,000 is workable but tight. Be conservative with feature count and aggressive with regularization.

---

## 6. The 60/40 XGBoost/Comp Blend — 🔴 CRITICAL: ARBITRARY, NOT OPTIMIZED

### The Problem
The plan specifies "60% XGBoost + 40% comp-based" with **zero justification** for this ratio. This is a **hyperparameter** that must be optimized, not guessed.

### How to Determine the Right Blend

**A. Treat it as a stacking problem**
- On the training set (with CV predictions from XGBoost), fit a simple linear blend:
  ```
  final = α * xgb_pred + (1-α) * comp_pred
  ```
- Optimize α by minimizing MAE on held-out CV folds
- This is literally a 1-parameter optimization — grid search over α ∈ [0, 0.1, 0.2, ..., 1.0]

**B. Use a meta-learner**
- Train a small Ridge regression on the two predictions as features
- This allows non-uniform weighting and can learn when to trust which model more
- With only 2 features, overfitting risk is negligible

**C. Expect the optimal α to vary by segment**
- For well-comped areas (dense Manhattan), comp-based may be better → α < 0.6
- For sparse areas (outer boroughs), XGBoost may be better → α > 0.6
- Consider **segment-specific blending** (different α per borough)

### Verdict
**Do not hardcode 60/40.** Optimize it. This is the single easiest improvement in the entire plan.

---

## 7. Data Leakage — ⚠️ MORE RISKS THAN IDENTIFIED

### What the Plan Identifies
- `availability_365` is partially a function of revenue — **correct, this is a real risk**

### What the Plan Misses

**A. `estimated_revenue_l365d` is derived from `price` and occupancy**
The target variable is computed as `occupied_nights × price`. If `price` is a feature AND part of the target's formula, you have **direct leakage**. The model will learn `revenue ≈ price × some_factor` instead of learning real patterns.
- **Fix:** Either (a) remove `price` as a feature and only use it in the comp-based path, or (b) use `price` but validate that the model isn't just learning the trivial relationship by checking if it outperforms a simple `price × 365 × occupancy_rate` baseline by a large margin.

**B. `reviews_per_month` and `number_of_reviews` are outcome variables**
More revenue → more stays → more reviews. These are **consequences** of revenue, not causes. Using them as features is a form of leakage.
- **Mitigation:** Use review metrics only as proxies for listing quality, and validate by checking if the model's performance drops significantly when review features are removed. If it doesn't drop, the model is learning real patterns. If it drops a lot, the model is relying on leakage.

**C. `host_listings_count` can be leakage for professional hosts**
A host with 50 listings generates revenue because of scale, not because of listing quality. The model may learn "more listings = more revenue per listing" which isn't causal.

**D. Train/test split by time, not random**
The plan does a random 80/20 split. But InsideAirbnb data has a temporal component (quarterly snapshots). If you're training on Q1 data and testing on Q2 data, a random split overestimates performance.
- **Recommendation:** If multiple quarterly snapshots are available, train on older data, test on newer data. If only one snapshot, random split is acceptable but document the limitation.

### Verdict
The `price → target` leakage is the most dangerous. Investigate it explicitly during EDA.

---

## 8. Train/Test Split Strategy — ⚠️ NEEDS IMPROVEMENT

### What's Good
- Stratified by borough — prevents Manhattan from dominating

### What's Wrong

**A. Stratification should be by revenue tier, not just borough**
A random 80/20 split stratified by borough may put all the $200K+ listings in the test set, making the model look worse than it is on high-revenue properties (which are the most interesting use case).

**B. Consider spatial stratification**
Listings near each other are correlated. A random split may put neighboring listings in train and test, inflating performance estimates.
- **Better:** Use spatial blocks (e.g., split by census tract or grid cell) so that nearby listings are in the same fold.
- **This is called "spatial cross-validation"** and is standard in geospatial ML.

**C. The 80/20 split with 5,000 samples leaves only 1,000 test cases**
For a production model, this is a thin test set. Consider:
- 70/30 split (3,500 train / 1,500 test) for more robust evaluation
- Or nested cross-validation (more complex but better use of data)

### Verdict
Add revenue-tier stratification. Consider spatial CV. The current split is adequate for MVP but not rigorous.

---

## 9. Feature Selection — ✅ YES, DO IT

### Why It Matters
With ~25 features and ~5,000 samples, you're at risk of:
- Curse of dimensionality (especially after one-hot encoding categoricals)
- Overfitting to noise features
- Slow training and unstable SHAP values

### Recommended Approach

**A. Pre-modeling: Correlation filter**
- Remove features with >0.95 correlation (e.g., `beds` and `accommodates` are likely highly correlated)
- This is cheap and eliminates redundancy

**B. During modeling: L1 regularization (Lasso)**
- Use XGBoost's `reg_alpha` parameter (L1 penalty) to induce sparsity
- Or train a Lasso regression first to identify which features have zero coefficient

**C. Post-modeling: SHAP-based selection**
- Train the full model, compute SHAP values
- Remove features with near-zero SHAP importance
- Re-train with reduced feature set
- This is the most principled approach but requires training twice

**D. Recursive Feature Elimination (RFE)**
- With 5,000 samples, RFE is computationally feasible
- Use it to find the optimal number of features (typically 10-15 for this dataset size)

### Verdict
**Do feature selection.** Start with correlation filtering, then use SHAP importance. Aim for 10-15 features max.

---

## 10. Overfitting and Generalization — 🔴 CRITICAL CONCERNS

### The Core Risk
With ~5,000 samples, ~25 features, and XGBoost (a model that can easily memorize), overfitting is the **primary threat**.

### Specific Concerns

**A. Hyperparameters are not tuned**
The plan specifies `max_depth=6, n_estimators=500, learning_rate=0.05` as fixed values. These are **not defaults** — they're a guess.
- `max_depth=6` is deep for 5,000 samples. Start with `max_depth=3-4`.
- `n_estimators=500` with `learning_rate=0.05` may overfit. Use early stopping with a validation set.
- **Recommendation:** Use Optuna or sklearn's `RandomizedSearchCV` for hyperparameter tuning. At minimum, tune: `max_depth`, `learning_rate`, `n_estimators`, `min_child_weight`, `subsample`, `colsample_bytree`, `reg_alpha`, `reg_lambda`.

**B. No regularization specified**
The plan doesn't mention `reg_alpha` (L1), `reg_lambda` (L2), `min_child_weight`, `subsample`, or `colsample_bytree`. These are **essential** for small datasets. Without them, XGBoost will overfit.

**C. No early stopping**
`n_estimators=500` without early stopping is asking for overfitting. Use early stopping with `eval_set` on a validation fold. Typical `n_estimators` after early stopping on a 5K dataset: 50-200.

**D. No feature importance sanity check**
SHAP values are mentioned, but there's no plan to **act on them**. If a feature has high importance but makes no domain sense, it's likely capturing noise or leakage.

**E. Generalization beyond NYC**
The plan correctly identifies this as a risk but doesn't address it. For MVP, NYC-only is fine. But document clearly:
- The model is NYC-specific
- Performance on other cities is unknown and likely worse
- A multi-city model would need 10x+ more data

### Verdict
**Tune hyperparameters. Add regularization. Use early stopping. This is non-negotiable.**

---

## Summary of Recommendations (Priority Order)

| Priority | Issue | Recommendation |
|----------|-------|----------------|
| 🔴 P0 | 60/40 blend is arbitrary | Optimize α via CV or meta-learner |
| 🔴 P0 | No hyperparameter tuning | Use Optuna or RandomizedSearchCV |
| 🔴 P0 | No regularization specified | Add reg_alpha, reg_lambda, min_child_weight, subsample, colsample_bytree |
| 🔴 P0 | No early stopping | Use eval_set with early_stopping_rounds=50 |
| 🔴 P0 | Price leakage into target | Investigate and mitigate; validate model isn't just learning revenue ≈ price × factor |
| ⚠️ P1 | Missing features | Add review recency, subway distance, host_response_rate |
| ⚠️ P1 | Monthly revenue endpoint is fabricated | Remove from API or add honest disclaimer |
| ⚠️ P1 | No feature selection | Correlation filter + SHAP-based selection |
| ⚠️ P1 | No stratified evaluation | Report metrics per borough and revenue tier |
| ⚠️ P1 | Confidence intervals unvalidated | Add coverage and sharpness metrics |
| 💡 P2 | Log-transform bias | Apply Duan's smearing correction |
| 💡 P2 | Spatial CV | Consider spatial cross-validation |
| 💡 P2 | Baseline other models | Train LightGBM, CatBoost, Ridge |
| 💡 P2 | Revenue-tier stratification | Stratify train/test split by revenue, not just borough |

---

## Overall Assessment

The plan demonstrates solid architectural thinking and the right strategic pivot (supervised learning on InsideAirbnb labels). The comp-finder + XGBoost hybrid is a sound approach. However, the **execution details are undercooked** — the model training section reads like a first draft, not a production plan. The lack of hyperparameter tuning, regularization, and the hardcoded blend ratio are the biggest red flags.

**With the P0 fixes implemented, this plan can produce a credible MVP.** Without them, you'll get an overfit model with an arbitrary blend that looks good on a small test set and fails in production.

**Estimated additional effort for P0 fixes:** 2-4 hours (mostly Optuna tuning + blend optimization + leakage investigation).

---

*End of audit.*
