# PREMORTEM — Assume the system failed. Why?

> Written as if the product shipped and users reported wrong estimates.
> Every finding is a plausible failure mode, not a theoretical concern.

---

## The Core Problem

**We built a prediction model that predicts predictions, not reality.**

The target variable (`estimated_revenue_l365d`) is InsideAirbnb's own estimate, computed as `occupied_nights × nightly_price` where `occupied_nights` is inferred from quarterly calendar snapshots. We are training on a PREDICTION with ~30-50% error baked in. The model can never be more accurate than its labels.

---

## Silent Failure #1: Training on Estimates, Not Reality

**What happens:** A user enters their property. The model predicts $40K/year. The actual revenue is $60K. The user makes a bad investment decision.

**Why:** The model was trained on InsideAirbnb's `estimated_revenue_l365d`, which is itself an estimate. The labels have ~30-50% error. The model learns this error as signal.

**Evidence:** The model's MAPE (63%) is worse than the noise in the training labels. The model is fitting to noise, not signal.

**Fix:** Use actual revenue data (from property managers, host surveys, or scraping actual booking data). Or: clearly label the tool as "estimated range" not "prediction."

---

## Silent Failure #2: The Simple Heuristic Beats the Model

**What happens:** A user compares our tool to a simple calculation. They find that `price × 365 × 0.5` gives better results 81% of the time.

**Why:** The model's Within 50% is 77.3%. A naive heuristic (50% occupancy assumption) achieves 81.4%. The model is WORSE than a rule of thumb.

**Evidence:**
```
Heuristic: price * 365 * 0.5
  MAPE: 92.1%
  Within 50%: 81.4%

Model:
  MAPE: 63.1%
  Within 50%: 77.3%
```

The model has lower average error but WORSE coverage. The heuristic is bimodal — either very close or very far. The model is consistently mediocre.

**Fix:** Either improve the model significantly (>85% Within 50%) or be honest that the tool provides "rough estimates" not "predictions."

---

## Silent Failure #3: Subway Feature Hurts Predictions

**What happens:** The model gives higher weight to listings near subway stations. But listings near subway stations earn LESS (noisy areas, commercial zones). The model systematically under-predicts for transit-adjacent properties.

**Why:** `subway_within_200m` has correlation -0.097 with revenue. It's a NEGATIVE predictor. But the model uses it as a positive signal because it correlates with other features (Manhattan, high density).

**Evidence:**
```
subway_within_200m=0: median revenue $78,795
subway_within_200m=1: median revenue $76,857
Correlation: -0.097
```

**Fix:** Remove the subway feature or recompute it with proper spatial analysis (distance to subway weighted by neighborhood quality).

---

## Silent Failure #4: Survivorship Bias Inflates Estimates

**What happens:** A user lists a new property. The model predicts $80K/year. The actual revenue is $40K. The user loses money.

**Why:** The training data only includes SUCCESSFUL listings (revenue > 0). Failed, delisted, or underperforming listings are excluded. The model learns from winners only.

**Evidence:** The dataset was filtered to `estimated_revenue_l365d > 0`. Listings with 0 revenue (failed, delisted, seasonal) are excluded. The median revenue in the training data ($79K) is likely 2-3x higher than the true market median.

**Fix:** Include failed/delisted listings in the training data. Or: add a disclaimer that estimates reflect "successful listings only."

---

## Silent Failure #5: Blend Alpha = 1.0 (Comp Finder is Dead Code)

**What happens:** The comp finder runs, finds similar listings, computes a weighted average. The model ignores it completely. Users see "5 comparable properties" but they don't affect the estimate.

**Why:** The blend optimization found α=1.0 (pure XGBoost). The comp-based prediction is never used. The entire `comp_finder.py` module is dead code.

**Evidence:**
```python
blend_alpha = 1.0  # From model metadata
final = 1.0 * model_pred + 0.0 * comp_pred  # = model_pred
```

**Fix:** Either optimize α < 1.0 (requires the model to be weaker) or remove the comp finder and be honest that estimates are model-only.

---

## Silent Failure #6: Spatial Reasoning is Broken

**What happens:** A user enters an address in a trendy neighborhood. The model predicts based on lat/lng coordinates. Two blocks away, a similar listing gets a very different prediction because XGBoost splits on a lat/lng threshold.

**Why:** XGBoost treats lat/lng as numeric features. It splits on `latitude > 40.7485`, not on "near Times Square." The model can't learn spatial relationships.

**Evidence:** Two listings 1km apart have lat diff ~0.009. XGBoost's tree splits create hard boundaries at arbitrary coordinate values, not smooth distance-based gradients.

**Fix:** Use spatial features (distance to landmarks, neighborhood clusters, spatial embeddings) instead of raw lat/lng.

---

## Silent Failure #7: Single-Price-Point for Annual Revenue

**What happens:** A user enters $200/night. The model predicts annual revenue. But the listing's actual price varies from $100 (winter) to $400 (events). The model assumes $200 every night.

**Why:** `price_num` is the CURRENT nightly rate from a single scrape. It's not the average rate over 12 months. Seasonal pricing, event pricing, and dynamic pricing are ignored.

**Evidence:** The training data has one price per listing (from the June 2026 scrape). Revenue is estimated over 12 months. A June price of $200 ≠ a January price of $100.

**Fix:** Use average price over multiple scrapes, or incorporate seasonal pricing models.

---

## Silent Failure #8: Confidence Intervals are Meaningless

**What happens:** A user sees "Revenue: $40K, Range: $28K-$148K." They don't know what to do with this. The range is too wide to be useful.

**Why:** The confidence interval is computed from comp variance, not model uncertainty. It's not calibrated. No coverage testing was done. The `level` is always "low" because finding 10+ similar listings is rare.

**Evidence:**
```
revenue_lower = min(comp_10th_pct, prediction * 0.7)
revenue_upper = max(comp_90th_pct, prediction * 1.3)
```

These are magic numbers (0.7x and 1.3x) with no statistical basis.

**Fix:** Use quantile regression or conformal prediction for calibrated intervals. Or: remove the intervals and show a single estimate with a disclaimer.

---

## Silent Failure #9: Property Type Encoding Destroys Information

**What happens:** A user has a "Entire villa" property. The model groups it into "Other" and treats it the same as a "Shared room." The prediction is wrong.

**Why:** Rare property types (<10 listings) are grouped into "Other." This destroys information about high-value properties.

**Evidence:**
```
prop_Entire rental unit: 66.3%
prop_Entire home: 11.7%
prop_Entire guest suite: 6.2%
prop_Entire condo: 2.7%
prop_Entire loft: 2.4%
prop_Entire townhouse: 4.8%
prop_Entire serviced apartment: 2.1%
prop_Room in aparthotel: 3.1%
```

Villas, cottages, and unique properties are lost in "Other."

**Fix:** Use property type as a continuous feature (price premium by type) instead of one-hot encoding.

---

## Silent Failure #10: Borough Distribution Bias

**What happens:** A user enters a Queens address. The model predicts based on 120 Queens listings. The prediction has high variance because the training data is sparse for Queens.

**Why:** Manhattan has 55% of training data, Brooklyn 32%, Queens 10%, Bronx 0%, Staten Island 0%. The model is biased toward Manhattan.

**Evidence:**
```
Manhattan: 640 listings (55%)
Brooklyn: 375 listings (32%)
Queens: 120 listings (10%)
Bronx: 0 listings (0%)
Staten Island: 0 listings (0%)
```

Bronx and Staten Island have zero representation. Queens has only 120 listings.

**Fix:** Oversample underrepresented boroughs or use borough-specific models.

---

## Summary: Top 5 Failure Modes by Impact

| Rank | Failure | Impact | Likelihood |
|------|---------|--------|------------|
| 1 | Training on estimates, not reality | Model can never be accurate | Certain |
| 2 | Simple heuristic beats model | Tool is not useful | Certain |
| 3 | Survivorship bias | Systematic over-prediction | Certain |
| 4 | Blend alpha=1.0, comp finder dead | No fallback when model is wrong | Certain |
| 5 | Spatial reasoning broken | Inconsistent predictions by location | High |

---

## What This Means

**The system will ship and produce confident, plausible, WRONG results.**

The model outputs a number with 5 significant digits. It looks precise. It looks authoritative. But it's built on:
- Predictions trained on predictions
- A model that's worse than a rule of thumb
- Dead code (comp finder) that creates false confidence
- Survivorship bias that inflates estimates
- Spatial features that don't work

**The honest assessment:** This tool should be labeled "rough estimate, ±50%, based on historical data from successful listings only" — not "revenue prediction."

**The path forward:**
1. Get actual revenue data (not estimates)
2. Fix spatial reasoning (use distance features, not raw lat/lng)
3. Calibrate confidence intervals
4. Make the comp finder actually contribute
5. Add failed/delisted listings to training data
6. Be transparent about limitations
