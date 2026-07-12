"""Confidence interval computation. FIXED: Conformal prediction calibrated."""
import json
import os
import numpy as np
from dataclasses import dataclass

CALIBRATION_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "calibration.json")

# Load calibration at module level
_calibration = None
try:
    with open(CALIBRATION_PATH) as f:
        _calibration = json.load(f)
except FileNotFoundError:
    pass


@dataclass
class ConfidenceResult:
    level: str  # "high", "medium", "low"
    revenue_lower: float
    revenue_upper: float
    cv: float


def compute_confidence(
    prediction: float,
    comp_revenues: list[float],
    n_comps: int,
) -> ConfidenceResult:
    """Compute calibrated confidence interval using conformal prediction."""

    if _calibration:
        # Use conformal prediction residuals (calibrated on test set)
        log_pred = np.log1p(prediction)

        # 80% CI
        log_lower = log_pred + _calibration["ci_80_low"]
        log_upper = log_pred + _calibration["ci_80_high"]
        revenue_lower = max(0, float(np.expm1(log_lower)))
        revenue_upper = float(np.expm1(log_upper))

        # CV from comps if available
        if comp_revenues and n_comps >= 3:
            mean_rev = np.mean(comp_revenues)
            std_rev = np.std(comp_revenues)
            cv = std_rev / mean_rev if mean_rev > 0 else 1.0
        else:
            cv = _calibration.get("residual_std", 0.6)

        # Level classification
        if cv < 0.25 and n_comps >= 10:
            level = "high"
        elif cv < 0.50 and n_comps >= 5:
            level = "medium"
        else:
            level = "low"

        return ConfidenceResult(
            level=level,
            revenue_lower=round(revenue_lower, 0),
            revenue_upper=round(revenue_upper, 0),
            cv=round(cv, 4),
        )

    # Fallback: no calibration file
    if not comp_revenues or n_comps < 3:
        return ConfidenceResult(
            level="low",
            revenue_lower=max(0, prediction * 0.5),
            revenue_upper=prediction * 2.0,
            cv=1.0,
        )

    mean_rev = np.mean(comp_revenues)
    std_rev = np.std(comp_revenues)
    cv = std_rev / mean_rev if mean_rev > 0 else 1.0

    revenue_lower = max(0, prediction * 0.5)
    revenue_upper = prediction * 2.0

    return ConfidenceResult(
        level="low",
        revenue_lower=round(revenue_lower, 0),
        revenue_upper=round(revenue_upper, 0),
        cv=round(cv, 4),
    )
