# MEMORY.md — Long-Term Memory

> Last updated: 2026-06-29 08:51 UTC

## Project: AirDNA Clone (Rentalizer)

### What It Is
Short-term rental revenue estimation tool. Predicts annual Airbnb revenue for NYC properties given address + property details.

### Current Status
- MVP built and running on port 8000
- LightGBM model v3.0.0, 52 features, R²=0.563, MdAPE=23.3%
- 10 premortem fixes applied
- No tests, no deployment yet

### Key Learnings
1. **Don't mix STR and LTR data** — 72% of training data was long-term rentals (min_nights=30). Filtered to min_nights < 30.
2. **Don't train on leaky features** — reviews_ltm (60% importance) was a proxy for the target. Removed.
3. **Don't trust R²=0.997** — It was from feature leakage, not real performance.
4. **InsideAirbnb already provides revenue estimates** — Use them as training labels, don't try to compute from calendar.
5. **Transit features need to be in both training AND inference** — They were in training but not inference, causing silent bias.
6. **Property type columns must match** — Inference created different one-hot columns than training.
7. **Conformal prediction for CIs** — Much better than arbitrary magic multipliers.
8. **Blend model + comps** — Model alone under-predicts for new listings. Comps provide real-world anchor.

### What's Left
- Tests (0 written)
- Deployment
- Multi-city support
- Real revenue validation

### Files to Read on Resume
1. `airdna-project/SESSION-RESUME.md` — Full session state
2. `airdna-project/08-rentalizer/PREMORTEM-AUDIT.md` — Latest audit
3. `memory/2026-06-29.md` — Today's detailed log
