"""AIRWORTHY score, verdict, and reason — the shared scoring model.

Positions AIRWORTHY as a property-readiness / investment-certification
system: every estimate resolves to a 0-100 score and one of four verdicts
(CLEARED / CONDITIONAL / EXPOSED / GROUNDED), never a fabricated or
unqualified "accuracy" number. The score is a transparent, deterministic
read of two signals *already present* in the estimate response — it never
changes the underlying revenue estimate itself:

  1. Earnings strength (0-60 pts) — how the projected annual revenue
     compares to the local market benchmark (the median revenue among the
     comparables actually used for this estimate).
  2. Estimate reliability (0-40 pts) — how tight the comparable-revenue
     spread is (coefficient of variation) and how many comparables support
     it (n_comps). This mirrors, but is independent from, the existing
     high/medium/low confidence level — that field is untouched.

Verdict thresholds are plain score bands, stated here so they can be
verified by reading this file rather than a tuned/hidden model.
"""
from dataclasses import dataclass

# --- Verdict score bands (0-100) ---
CLEARED_MIN = 75      # score >= 75  -> CLEARED
CONDITIONAL_MIN = 55  # score >= 55  -> CONDITIONAL
EXPOSED_MIN = 35       # score >= 35  -> EXPOSED
# score < EXPOSED_MIN  -> GROUNDED

VERDICT_MEANINGS = {
    "CLEARED": "Strong projected performance",
    "CONDITIONAL": "Viable performance under current assumptions",
    "EXPOSED": "Financially sensitive projection",
    "GROUNDED": "Insufficient earnings potential",
}


@dataclass
class AirworthyResult:
    score: int
    verdict: str
    reason: str


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _earnings_score(annual_revenue: float, benchmark_revenue: float) -> tuple[float, float]:
    """0-60 pts from projected revenue vs. the local market benchmark.

    ratio == 1.0 (matches the local benchmark exactly) -> 30 pts (midpoint).
    Every +10% above the benchmark adds 5 pts, every -10% below subtracts
    5 pts, clamped to [0, 60]. A missing/zero benchmark can't support a
    directional claim, so it falls back to the midpoint with ratio=1.0.
    """
    if not benchmark_revenue or benchmark_revenue <= 0:
        return 30.0, 1.0
    ratio = annual_revenue / benchmark_revenue
    score = 30.0 + (ratio - 1.0) * 50.0
    return _clamp(score, 0.0, 60.0), ratio


def _reliability_score(cv: float, n_comps: int) -> float:
    """0-40 pts from comparable-revenue spread (cv) and comparable count.

    cv (coefficient of variation) contributes up to 28 pts on a linear
    slide: cv=0 -> 28 pts, cv>=1.0 -> 0 pts. Comparable count contributes
    up to 12 pts: n_comps>=20 -> 12 pts, n_comps=0 -> 0 pts.
    """
    cv = max(0.0, cv)
    cv_score = _clamp(28.0 * (1.0 - min(cv, 1.0)), 0.0, 28.0)
    n_score = _clamp(12.0 * (min(max(n_comps, 0), 20) / 20.0), 0.0, 12.0)
    return cv_score + n_score


def _verdict_for(score: float) -> str:
    if score >= CLEARED_MIN:
        return "CLEARED"
    if score >= CONDITIONAL_MIN:
        return "CONDITIONAL"
    if score >= EXPOSED_MIN:
        return "EXPOSED"
    return "GROUNDED"


def _reason_for(verdict: str, ratio: float, cv: float, n_comps: int) -> str:
    pct = round((ratio - 1.0) * 100)
    if pct >= 5:
        earnings_bit = f"projects {abs(pct)}% above the local market benchmark"
    elif pct <= -5:
        earnings_bit = f"projects {abs(pct)}% below the local market benchmark"
    else:
        earnings_bit = "projects in line with the local market benchmark"

    if cv < 0.25 and n_comps >= 15:
        reliability_bit = "backed by a tight, well-supported comparable set"
    elif cv < 0.5 and n_comps >= 8:
        reliability_bit = "backed by a reasonably consistent comparable set"
    else:
        reliability_bit = "supported by a thinner or more scattered comparable set"

    return f"{VERDICT_MEANINGS[verdict]} — {earnings_bit}, {reliability_bit}."


def compute_airworthy(annual_revenue: float, benchmark_revenue: float, cv: float, n_comps: int) -> AirworthyResult:
    """Compute the AIRWORTHY score (0-100), verdict, and a one-line reason.

    `benchmark_revenue` should be the median revenue of the market/comp set
    backing this estimate (already present in the response as
    `market.median_revenue`). `cv` and `n_comps` are the same coefficient of
    variation and comparable count already used for the confidence level.
    """
    earnings_pts, ratio = _earnings_score(annual_revenue, benchmark_revenue)
    reliability_pts = _reliability_score(cv, n_comps)
    score = int(round(_clamp(earnings_pts + reliability_pts, 0.0, 100.0)))
    verdict = _verdict_for(score)
    reason = _reason_for(verdict, ratio, cv, n_comps)
    return AirworthyResult(score=score, verdict=verdict, reason=reason)
