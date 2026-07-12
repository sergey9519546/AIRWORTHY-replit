"""Shared derived-metric helpers for the /v1/estimate response.

Used by both the NYC ML path and the comp-based market path so the two
estimators produce a consistent, richer contract: an average nightly rate
(ADR) and expected occupancy, a modeled 12-month revenue forecast, small
rule-based performance drivers, and structured confidence reasons. None of
this changes which properties get an estimate or how the point estimate
itself is computed — it only enriches the response around it.
"""

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# General US short-term-rental seasonality curve (index ~1.0 = an average
# month): soft in deep winter, ramping into spring, peaking in summer, with
# a secondary bump around the winter holidays. This is a MODELED shape
# blended with the property's own market data — not observed booking
# history for any specific listing.
_SEASONALITY = [0.80, 0.83, 0.92, 1.00, 1.06, 1.16,
                1.22, 1.18, 1.02, 0.92, 0.86, 1.03]
_SEASONALITY_SUM = sum(_SEASONALITY)
SEASONALITY = [12 * s / _SEASONALITY_SUM for s in _SEASONALITY]


def estimate_adr_occupancy(annual_revenue: float, nightly_rate: float) -> tuple[float, float]:
    """Derive an average daily rate (ADR) and an implied occupancy rate.

    ADR blends the user's asking nightly rate with what the modeled annual
    revenue implies at a typical baseline occupancy, so an unusually
    low/high asking price doesn't dominate the figure. Occupancy is then
    backed out from revenue / (ADR * 365) and clamped to a plausible STR
    range so degenerate inputs can't produce >100% or near-0% occupancy.
    """
    baseline_occupancy = 0.55
    implied_adr = annual_revenue / (365 * baseline_occupancy) if annual_revenue > 0 else nightly_rate
    adr = 0.6 * nightly_rate + 0.4 * implied_adr
    adr = max(20.0, adr)
    occupancy = annual_revenue / (adr * 365) if adr > 0 else 0.0
    occupancy = min(0.95, max(0.15, occupancy))
    return round(adr, 0), round(occupancy, 3)


def monthly_forecast(annual_revenue: float, cv: float) -> list[dict]:
    """Modeled 12-month expected/low/high revenue split.

    Applies a general seasonality curve to the annual estimate, then widens
    the low/high band using the estimate's own coefficient of variation so
    lower-confidence properties get a visibly wider forecast band.
    """
    band = min(0.6, max(0.12, cv))
    out = []
    for name, idx in zip(MONTH_NAMES, SEASONALITY):
        expected = annual_revenue / 12 * idx
        out.append({
            "month": name,
            "expected": round(expected, 0),
            "low": round(expected * (1 - band), 0),
            "high": round(expected * (1 + band), 0),
        })
    return out


def performance_drivers(
    nightly_rate: float,
    bedrooms: int,
    median_price: float,
    n_comps: int,
    is_superhost: bool = False,
    avg_distance_km: float | None = None,
) -> list[dict]:
    """Small rule-based explanation of what pushes the estimate up or down.

    Each driver is plain-language with an estimated dollar impact — a rough,
    directional annualized figure, not a precise attribution.
    """
    drivers: list[dict] = []

    if median_price and median_price > 0:
        pct = (nightly_rate - median_price) / median_price
        if abs(pct) >= 0.05:
            impact = (nightly_rate - median_price) * 0.55 * 365
            drivers.append({
                "label": f"Priced {abs(pct) * 100:.0f}% {'above' if pct > 0 else 'below'} nearby comparables",
                "direction": "positive" if pct > 0 else "negative",
                "impact_dollars": round(impact, 0),
            })

    if bedrooms >= 3:
        drivers.append({
            "label": f"{bedrooms}-bedroom layout appeals to larger groups",
            "direction": "positive",
            "impact_dollars": round(1800.0 * (bedrooms - 2), 0),
        })
    elif bedrooms <= 1:
        drivers.append({
            "label": "Studio/1-bedroom layout limits group size and rate ceiling",
            "direction": "negative",
            "impact_dollars": -1200.0,
        })

    if is_superhost:
        drivers.append({
            "label": "Superhost status increases guest trust and booking rate",
            "direction": "positive",
            "impact_dollars": 1500.0,
        })

    if avg_distance_km is not None:
        if avg_distance_km <= 1.5:
            drivers.append({
                "label": "Sits right in the middle of a strong comparable cluster",
                "direction": "positive",
                "impact_dollars": 800.0,
            })
        elif avg_distance_km > 8:
            drivers.append({
                "label": "Farther from the core of comparable listings, adding uncertainty",
                "direction": "negative",
                "impact_dollars": -800.0,
            })

    if n_comps < 8:
        drivers.append({
            "label": "Limited number of nearby comparables narrows pricing confidence",
            "direction": "negative",
            "impact_dollars": -500.0,
        })

    return drivers


def confidence_reasons(
    n_comps: int,
    avg_distance_km: float,
    cv: float,
    data_freshness: str,
    bedroom_match_ratio: float = 1.0,
) -> tuple[list[str], list[str]]:
    """Structured reasons behind the confidence level, plus disclosed weaknesses."""
    reasons = [f"Based on {n_comps} comparable listings near this address"]

    if avg_distance_km <= 2:
        reasons.append(f"Comparables are close by (avg {avg_distance_km:.1f} km)")
    else:
        reasons.append(f"Comparables average {avg_distance_km:.1f} km away")

    if bedroom_match_ratio >= 0.7:
        reasons.append("Most comparables match this property's bedroom count")

    if data_freshness:
        reasons.append(f"Market data current as of {data_freshness}")

    weaknesses = []
    if n_comps < 8:
        weaknesses.append("Fewer comparables than ideal — the estimate has wider uncertainty")
    if cv >= 0.5:
        weaknesses.append("Comparable revenues vary widely, reducing precision")
    if bedroom_match_ratio < 0.5:
        weaknesses.append("Few comparables share this property's exact bedroom count")

    return reasons, weaknesses
