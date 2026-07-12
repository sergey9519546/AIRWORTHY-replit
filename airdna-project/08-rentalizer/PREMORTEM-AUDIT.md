# RENTALIZER — FORMAL PREMORTEM AUDIT

> Principal engineer premortem. Assume the system shipped, produced wrong results confidently, and nobody noticed.

---

## Context

```
SYSTEM: Short-term rental revenue estimation tool for NYC properties.
ENGINE: LightGBM model (52 features) + KD-Tree comp finder + smart blend.
USERS: Real estate investors evaluating NYC properties for Airbnb.
STAKES: Users invest $300K-$1M+ based on revenue estimates. Wrong estimates → bad investment → financial loss.
DEFINITION OF CORRECT: Annual revenue estimate within 50% of actual revenue for a real NYC STR listing.
DEFINITION OF FEATURE COMPLETE: A feature is complete only if it produces correct output across all realistic input shapes, handles failures visibly, and does not silently fall back to defaults.
```

---

## 1. Inventory Matrix

| Item | Type | Purpose | File:Line | Inputs | Outputs | Downstream | Status |
|------|------|---------|-----------|--------|---------|------------|--------|
| `load_model()` | ENGINE_RULE | Load ML model from disk | model.py:20-42 | File paths | Model object | `predict()` | FULLY WIRED |
| `predict()` | CALCULATION | Predict log revenue | model.py:45-55 | Feature dict | float | api.py blend | FULLY WIRED |
| `build_index()` | STATE_TRANSITION | Build KD-Tree from training data | comp_finder.py:35-65 | DataFrame | Global state | `find_comps()` | FULLY WIRED |
| `find_comps()` | ENGINE_RULE | Find comparable listings | comp_finder.py:68-120 | lat,lng,beds,cap | list[Comp] | blend, confidence | FULLY WIRED |
| `_score_comp()` | CALCULATION | Score comparable similarity | comp_finder.py:148-170 | listing,dist,beds,cap | float | `find_comps()` | PARTIAL |
| `predict_from_comps()` | CALCULATION | Weighted average of comp revenues | comp_finder.py:173-184 | list[Comp] | (float,float) | api.py blend | FULLY WIRED |
| `build_features()` | ENGINE_RULE | Build feature vector for inference | features.py:30-85 | User input + comps | dict | `predict()` | PARTIAL |
| `get_borough_from_coords()` | ENGINE_RULE | Determine borough from lat/lng | features.py:88-105 | lat,lng | str | `build_features()` | FULLY WIRED |
| `geocode()` | INTEGRATION | Convert address to lat/lng | geocoder.py:58-82 | str | GeocodeResult | validation, comps | FULLY WIRED |
| `validate_input()` | ENGINE_RULE | Validate user inputs | validation.py:12-35 | Request fields | warnings | api.py | FULLY WIRED |
| `validate_nyc_bounds()` | ENGINE_RULE | Check coordinates in NYC | validation.py:38-46 | lat,lng | raise/ok | api.py | FULLY WIRED |
| `compute_confidence()` | CALCULATION | Compute confidence interval | confidence.py:18-60 | prediction,comps,n | ConfidenceResult | api.py response | PARTIAL |
| Smart blend (api.py) | ENGINE_RULE | Blend model + comp predictions | api.py:145-175 | model_rev,comp_rev | float | response | FULLY WIRED |
| `TransitFeatureBuilder` | FEATURE | Subway proximity features | transit_features.py:18-80 | lat,lng | dict | NOT USED AT INFERENCE | DECORATIVE |
| `estimate()` | API_ENDPOINT | Main estimation endpoint | api.py:120-195 | EstimateRequest | EstimateResponse | Frontend | FULLY WIRED |
| `batch_estimate()` | API_ENDPOINT | Batch estimation | api.py:198-215 | list[Request] | list[Response] | Frontend | FULLY WIRED |
| Frontend form | FEATURE | User input form | index.html:28-55 | User input | JSON body | API | FULLY WIRED |
| Frontend results | FEATURE | Display results | app.js:45-130 | API response | DOM | User | FULLY WIRED |
| Leaflet map | FEATURE | Show property on map | app.js:132-165 | lat,lng | Map | User | FULLY WIRED |

---

## 2. Feature / Tool Completeness Matrix

| Feature | Claim | Actual Wiring | Evidence | Breakpoint | Risk | Confidence |
|---------|-------|---------------|----------|------------|------|------------|
| Revenue estimation | Estimate annual STR revenue | Model predicts, blend with comps | api.py:120-195 | New listing with no comps | Correct output not guaranteed | verified |
| Confidence intervals | Show revenue range | Comp variance + magic multipliers | confidence.py:30-55 | Always | Not calibrated, always "low" | verified |
| Comp finder | Find similar listings | KD-Tree + filter + score | comp_finder.py:68-120 | Listing outside NYC | Works but bathroom score hardcoded | verified |
| Borough detection | Identify NYC borough | GeoJSON polygon + bounding box fallback | features.py:88-105 | Point on borough boundary | Boundary points may misclassify | verified |
| Geocoding | Address → lat/lng | Mapbox primary, Nominatim fallback | geocoder.py:58-82 | Address not found | Raises GeocodingError | verified |
| NYC bounds check | Reject non-NYC addresses | Bounding box validation | validation.py:38-46 | Address in NJ/LI within box | Loose box admits non-NYC | verified |
| Transit features | Subway proximity | KD-Tree on 50 stations | transit_features.py:18-80 | At inference time | NOT USED — dead code at inference | verified |
| Map display | Show property location | Leaflet + OSM tiles | app.js:132-165 | Leaflet CDN down | Falls back to OSM iframe | verified |
| Batch endpoint | Multiple estimates | Sequential processing | api.py:198-215 | >20 items | Returns 413 | verified |
| Rate limiting | Prevent abuse | slowapi 30/min | api.py:118 | No API key configured | Works but dev mode bypasses auth | verified |

---

## 3. Engine Logic Findings

### F1: `_score_comp()` Bathroom Score is Hardcoded to 0.15 (Severity: 7)

| Field | Value |
|-------|-------|
| Logic | Bathroom match scoring in comp finder |
| Should Do | Score comps by bathroom match (15% of total) |
| Actually Does | Always returns 0.15 for every comp |
| Divergence | 15% of the comp score is wasted — all comps get identical bathroom score |
| Evidence | `comp_finder.py:163` — `bath_score = 0.15` with comment "Default full score since we don't have target bathrooms" |
| Scenario | 1-bath target vs 3-bath comp gets same score as 1-bath vs 1-bath |
| Risk | Comp ranking is wrong when bathrooms differ significantly |
| Fix | Pass `target_bathrooms` to `_score_comp()` and compute actual match |
| Confidence | verified from code |

### F2: `build_features()` Hardcodes `minimum_nights_num = 1` (Severity: 6)

| Field | Value |
|-------|-------|
| Logic | Minimum nights feature for model prediction |
| Should Do | Use actual minimum nights from the listing |
| Actually Does | Always sets to 1 |
| Divergence | The model's #2 feature (16.6% importance) is always 1 at inference, but was trained on listings with min_nights 1-29 |
| Evidence | `features.py:50` — `features["minimum_nights_num"] = 1` |
| Scenario | A listing with min_nights=7 (common for STR) gets predicted as min_nights=1 |
| Risk | Systematic bias — model learned that min_nights matters but inference always says 1 |
| Fix | Accept min_nights as user input or default to market median |
| Confidence | verified from code |

### F3: `build_features()` Hardcodes `host_listings_count_num = 1` (Severity: 6)

| Field | Value |
|-------|-------|
| Logic | Host listing count feature |
| Should Do | Use actual host listing count |
| Always sets to 1 |
| Divergence | Model trained with host_listings_count ranging 1-263, but inference always 1 |
| Evidence | `features.py:49` |
| Scenario | Professional host (50 listings) gets predicted as single-property host |
| Risk | Under-predicts for professional hosts, over-predicts for single-property hosts |
| Fix | Accept as user input or estimate from listing quality |
| Confidence | verified from code |

### F4: `build_features()` Hardcodes `superhost_num = 0` (Severity: 6)

| Field | Value |
|-------|-------|
| Logic | Superhost status feature |
| Should Do | Use actual superhost status |
| Actually Does | Always sets to 0 |
| Divergence | Model trained with 40% superhost listings, inference always non-superhost |
| Evidence | `features.py:51` |
| Scenario | Superhost listing gets predicted as non-superhost |
| Risk | Under-predicts for superhosts (superhost is 3.9% importance) |
| Fix | Accept as user input |
| Confidence | verified from code |

### F5: `build_features()` Hardcodes All Amenities to Defaults (Severity: 5)

| Field | Value |
|-------|-------|
| Logic | Amenity features for model |
| Should Do | Use actual listing amenities |
| Actually Does | wifi=1, kitchen=1, others=0 (or from borough defaults) |
| Divergence | Model trained with varying amenity profiles, inference uses fixed defaults |
| Evidence | `features.py:60-73` |
| Scenario | Listing with pool/gym gets predicted as having neither |
| Risk | Wrong predictions for amenity-rich or amenity-poor properties |
| Fix | Accept amenities as user input or parse from listing URL |
| Confidence | verified from code |

### F6: `compute_confidence()` Uses Magic Multipliers (Severity: 8)

| Field | Value |
|-------|-------|
| Logic | Confidence interval computation |
| Should Do | Produce calibrated confidence intervals |
| Actually Does | `lower = min(p10, prediction * 0.7)`, `upper = max(p90, prediction * 1.3)` |
| Divergence | 0.7x and 1.3x are arbitrary. No statistical basis. Not calibrated. |
| Evidence | `confidence.py:38-39` |
| Scenario | A $50K prediction gets range $35K-$65K regardless of actual uncertainty |
| Risk | Users see precise-looking ranges that are meaningless |
| Fix | Use quantile regression or conformal prediction |
| Confidence | verified from code |

### F7: `compute_confidence()` Level Always "low" in Practice (Severity: 7)

| Field | Value |
|-------|-------|
| Logic | Confidence level classification |
| Should Do | Classify as high/medium/low based on data quality |
| Actually Does | Downgrades to "low" when n_comps < 5 (line 52) or when n_comps < 10 and level was "high" (line 54) |
| Divergence | Finding 5+ similar comps is rare for unique properties → always "low" |
| Evidence | `confidence.py:50-55` |
| Scenario | Any property with < 5 comps gets "low" regardless of comp quality |
| Risk | Users lose trust when every result says "low confidence" |
| Fix | Adjust thresholds or use model uncertainty instead of comp count |
| Confidence | verified from code |

### F8: Blend Alpha Logic Has Dead Branch (Severity: 5)

| Field | Value |
|-------|-------|
| Logic | Smart blend in api.py |
| Should Do | Dynamically blend model + comps |
| Actually Does | When < 3 comps, uses model only (line 173) |
| Divergence | The fallback path (`final_log_revenue = log_revenue`) uses the raw model prediction, which under-predicts for new listings |
| Evidence | `api.py:172-174` |
| Scenario | Listing in sparse area (few comps) → model-only prediction → $18K instead of $80K |
| Risk | Worst predictions happen exactly where they matter most (sparse areas) |
| Fix | Fall back to market median when comps are insufficient |
| Confidence | verified from code |

### F9: `features.py` Prop Types Don't Match Training Data (Severity: 6)

| Field | Value |
|-------|-------|
| Logic | Property type one-hot encoding |
| Should Do | Create same columns as training data |
| Actually Does | Creates columns for: Entire rental unit, Entire home, Entire condo, Entire loft, Entire townhouse, Entire guest suite, Entire guest house, Entire cottage, Entire place, Other |
| Divergence | Training data has: Entire condo, Entire guest suite, Entire home, Entire loft, Entire rental unit, Entire serviced apartment, Entire townhouse, Room in aparthotel |
| Evidence | `features.py:64-70` vs training data columns |
| Scenario | "Entire serviced apartment" and "Room in aparthotel" exist in training but not in inference. "Entire guest house" and "Entire cottage" exist in inference but not training. |
| Risk | Property type feature is always 0 for missing columns → model can't distinguish property types |
| Fix | Use exact same property types as training data |
| Confidence | verified from code |

### F10: `_find_comps_relaxed()` Returns All Listings Without Filtering (Severity: 6)

| Field | Value |
|-------|-------|
| Logic | Fallback comp finder when main finds < 3 |
| Should Do | Find reasonable comps with relaxed filters |
| Actually Does | Returns top K nearest listings regardless of bedrooms/accommodates |
| Divergence | A 5-bedroom penthouse gets comps that include studios |
| Evidence | `comp_finder.py:125-145` — no bedroom/capacity filter |
| Scenario | Unique property → relaxed finder → comps are completely wrong → bad prediction |
| Risk | The fallback produces worse results than no comps at all |
| Fix | At minimum filter by same room_type, or return empty and use market median |
| Confidence | verified from code |

---

## 4. Silent Default / Fallback Findings

| Location | Failure Case | Silent Default Used | Caller Notified? | Plausible Wrong Output | Should Instead | Risk | Confidence |
|----------|-------------|--------------------|--------------------|----------------------|----------------|------|------------|
| `features.py:49` | No host data | `host_listings_count_num = 1` | No | Under-predicts for professional hosts | Accept as input or use market median | 6 | verified |
| `features.py:50` | No min_nights data | `minimum_nights_num = 1` | No | Wrong prediction (model's #2 feature) | Accept as input | 6 | verified |
| `features.py:51` | No superhost data | `superhost_num = 0` | No | Under-predicts for superhosts | Accept as input | 6 | verified |
| `features.py:53` | No instant_bookable data | `instant_bookable_num = 0` | No | Minor bias | Accept as input | 4 | verified |
| `features.py:54` | No host experience | `host_experience_months = 36` | No | Minor bias | Accept as input | 3 | verified |
| `features.py:60-73` | No amenity data | Hardcoded defaults | No | Wrong for amenity-rich/poor properties | Accept as input | 5 | verified |
| `features.py:64-70` | Property type not in training | Creates columns not in model | No | Feature vector mismatch | Use exact training column set | 6 | verified |
| `confidence.py:22-27` | < 3 comps | `level="low"`, `lower=pred*0.5`, `upper=pred*2.0` | No | Useless range | Use market statistics | 7 | verified |
| `confidence.py:38-39` | Always | `lower=min(p10, pred*0.7)`, `upper=max(p90, pred*1.3)` | No | Arbitrary range | Calibrate with conformal prediction | 8 | verified |
| `comp_finder.py:163` | No target bathrooms | `bath_score = 0.15` | No | Wrong comp ranking | Pass target bathrooms | 7 | verified |
| `comp_finder.py:125-145` | < 3 comps found | Returns nearest K without filtering | No | Completely wrong comps | Return empty, use market median | 6 | verified |
| `geocoder.py:46-50` | Mapbox fails | Falls back to Nominatim | No (log only) | Different geocoding result | Surface warning to user | 4 | verified |
| `api.py:172-174` | < 3 comps | Uses model only | No | $18K instead of $80K | Fall back to market median | 8 | verified |
| `model.py:33-35` | Meta file not found | `{"version": "unknown", "metrics": {}}` | No (log only) | Model info shows "unknown" | Fail startup | 4 | verified |

---

## 5. Cross-Feature / Cross-Rule Collisions

| Collision | Components | Shared State | Current Winner | Deterministic? | Intended? | Risk | Evidence | Fix |
|-----------|------------|-------------|----------------|----------------|-----------|------|----------|-----|
| Borough from GeoJSON vs Borough from one-hot | `get_borough_from_coords()` vs `build_features()` | Borough string | `get_borough_from_coords()` | Yes | Yes | Low | api.py:140 calls both | None needed |
| Blend alpha from metadata vs dynamic blend | `_meta_blend_alpha()` vs api.py:145-175 | Blend weight | Dynamic blend (overrides metadata) | Yes | Yes | Low | api.py:145 always runs | None needed |
| Feature count in model vs feature count in inference | model.py `_features` vs features.py `build_features()` | Feature vector | model.py | Yes | Yes | High | If features.py creates wrong columns, model gets wrong vector | Validate feature names at startup |
| Transit features in training vs inference | `add_enhanced_features.py` vs `features.py` | Feature columns | Training adds them, inference doesn't | No | No | High | Model trained with transit features, inference uses 0 | Remove transit from training or add to inference |
| Property type encoding mismatch | Training data columns vs `features.py` columns | One-hot columns | Mismatch | No | No | High | "Entire serviced apartment" in training, not in inference | Align column sets |
| Comp revenue vs model revenue blend | `predict_from_comps()` vs `predict()` | Revenue estimate | Dynamic blend | Yes | Yes | Medium | Blend logic may mask model errors | Log blend decisions |

---

## 6. Top 10 Risks by Likelihood × Impact

| Rank | Finding | Likelihood | Impact | Score | Why It Matters | Evidence | First Fix |
|------|---------|-----------|--------|-------|----------------|----------|-----------|
| 1 | Property type encoding mismatch (F9) | 10 | 9 | 90 | Every prediction uses wrong property type features. Model can't distinguish property types. | features.py:64-70 vs training columns | Align inference columns to training columns |
| 2 | Transit features in training but not inference | 9 | 8 | 72 | Model expects transit features that are always 0 at inference. Systematic bias. | add_enhanced_features.py vs features.py | Remove transit from training OR add to inference |
| 3 | Confidence intervals are arbitrary (F6) | 10 | 7 | 70 | Every user sees a meaningless range. Erodes trust. | confidence.py:38-39 | Calibrate with conformal prediction |
| 4 | Model under-predicts for new listings (F8) | 9 | 7 | 63 | Worst predictions happen in sparse areas where users need help most | api.py:172-174 | Fall back to market median |
| 5 | min_nights hardcoded to 1 (F2) | 8 | 7 | 56 | Model's #2 feature is wrong for every prediction | features.py:50 | Accept as user input |
| 6 | Bathroom score hardcoded (F1) | 8 | 6 | 48 | 15% of comp score is wasted | comp_finder.py:163 | Pass target_bathrooms |
| 7 | Relaxed comp finder returns wrong comps (F10) | 6 | 8 | 48 | Unique properties get completely wrong comps | comp_finder.py:125-145 | Return empty, use market median |
| 8 | superhost hardcoded to 0 (F4) | 8 | 5 | 40 | Under-predicts for superhosts | features.py:51 | Accept as user input |
| 9 | host_listings_count hardcoded to 1 (F3) | 8 | 5 | 40 | Wrong for professional hosts | features.py:49 | Accept as user input |
| 10 | Confidence always "low" (F7) | 9 | 4 | 36 | Users lose trust | confidence.py:50-55 | Adjust thresholds |

---

## 7. Already Solid

| Item | Why It Appears Solid | Evidence | Confidence |
|------|---------------------|----------|------------|
| Geocoding with thread-safe cache | Singleton pattern, lock-protected cache, URL encoding | geocoder.py:58-82 | verified |
| NYC bounds validation | Simple, clear, raises on failure | validation.py:38-46 | verified |
| Borough detection (GeoJSON) | Polygon lookup with bounding box fallback | features.py:88-105 | verified |
| KD-Tree comp finding | Correct haversine conversion, vectorized lookup | comp_finder.py:35-65 | verified |
| XSS-safe frontend | All DOM manipulation uses textContent, no innerHTML with user data | app.js:45-130 | verified |
| Error handling in load_model | Try/except with ModelNotReadyError | model.py:20-42 | verified |
| Thread-safe geocoder | Lock-protected cache and singleton | geocoder.py:25-35 | verified |
| Input validation | Clear bounds, raises InvalidInputError | validation.py:12-35 | verified |
| API response structure | Pydantic models enforce schema | schemas.py:1-80 | verified |
| Disclaimer in every response | Present in EstimateResponse | api.py:188 | verified |

---

## 8. Unverifiable Items

| Item | Why Static Code Cannot Verify It | Required Runtime Check | Owner Decision Needed? |
|------|--------------------------------|----------------------|----------------------|
| Model accuracy on new data | Model was trained on one snapshot, tested on same snapshot | Test on different time period or city | Yes — decide if accuracy is acceptable |
| Geocoding accuracy for edge cases | Can't verify if "123 Main St" geocodes correctly without calling API | Test with 100 real addresses | No |
| Comp quality for sparse areas | Can't verify comp relevance without seeing actual listings | Test with properties in Staten Island, Bronx | Yes — decide minimum comp quality |
| Nominatim rate limiting | Can't verify behavior under load | Send 100 concurrent requests | No |
| LightGBM feature importance at inference | Can't verify model uses features correctly without runtime SHAP | Run SHAP on inference predictions | No |
| InsideAirbnb label accuracy | Can't verify if `estimated_revenue_l365d` is accurate | Compare to actual revenue data from hosts | Yes — decide if labels are trustworthy |

---

## 9. Suggested Tests

| Test Name | Scenario | Expected Result | Failure It Catches | Priority |
|-----------|----------|----------------|-------------------|----------|
| `test_property_type_alignment` | Check inference columns match training columns exactly | All training columns present in inference | F9: property type mismatch | P0 |
| `test_transit_features_in_inference` | Check if transit features are used at inference | Transit features should be 0 OR removed from model | Transit training/inference mismatch | P0 |
| `test_min_nights_impact` | Same property with min_nights=1 vs 7 vs 14 | Different predictions | F2: min_nights hardcoded | P0 |
| `test_blend_with_zero_comps` | Property with 0 comps found | Uses market median, not raw model | F8: dead fallback branch | P0 |
| `test_confidence_calibration` | 100 predictions, check if actual falls in CI 80% of time | ~80% coverage | F6: arbitrary intervals | P1 |
| `test_bathroom_score_variation` | 1-bath target vs 1-bath comp vs 3-bath comp | Different scores | F1: hardcoded bathroom score | P1 |
| `test_relaxed_comp_finder` | Property with < 3 main comps | Should return empty or filtered comps | F10: unfiltered fallback | P1 |
| `test_borough_boundary` | Address on Manhattan/Brooklyn boundary | Consistent borough | Boundary misclassification | P2 |
| `test_nj_address_rejected` | Address in Jersey City | Returns 422 | NYC bounds too loose | P2 |
| `test_superhost_impact` | Same property with superhost=0 vs 1 | Different predictions | F4: superhost hardcoded | P2 |
| `test_model_vs_heuristic` | Compare model to `price * 365 * 0.5` | Model should beat heuristic on Within 50% | Model may be worse than rule of thumb | P1 |
| `test_feature_vector_validation` | Check feature count and names at startup | Exactly 52 features in correct order | Silent feature mismatch | P0 |

---

## Execution Priority

**Fix now (P0):**
1. Align property type columns (F9) — 10 min
2. Remove transit features from training OR add to inference — 15 min
3. Add min_nights as user input (F2) — 10 min
4. Validate feature vector at startup — 10 min
5. Fix blend fallback to use market median (F8) — 10 min

**Fix next (P1):**
6. Fix bathroom score in comp finder (F1) — 10 min
7. Fix relaxed comp finder to return empty (F10) — 5 min
8. Add superhost/host_listings as user inputs — 15 min
9. Calibrate confidence intervals — 30 min

**Fix later (P2):**
10. Tighten NYC bounds — 10 min
11. Adjust confidence thresholds — 10 min
