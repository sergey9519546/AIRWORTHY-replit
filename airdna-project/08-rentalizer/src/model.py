"""Model loading and prediction. FIXED: proper error handling."""
import json
import logging
import numpy as np
import joblib

from .config import settings
from .exceptions import ModelNotReadyError

logger = logging.getLogger(__name__)

_model = None
_meta = None
_features = None


def load_model():
    """Load trained model and metadata. Raises ModelNotReadyError on failure."""
    global _model, _meta, _features

    try:
        _model = joblib.load(settings.MODEL_PATH)
        logger.info(f"Loaded model from {settings.MODEL_PATH}")
    except FileNotFoundError:
        raise ModelNotReadyError(f"Model file not found: {settings.MODEL_PATH}")
    except Exception as e:
        raise ModelNotReadyError(f"Failed to load model: {e}")

    try:
        with open(settings.META_PATH) as f:
            _meta = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Meta file not found: {settings.META_PATH}")
        _meta = {"version": "unknown", "metrics": {}}

    try:
        with open(settings.FEATURES_PATH) as f:
            _features = json.load(f)["features"]
    except FileNotFoundError:
        raise ModelNotReadyError(f"Features file not found: {settings.FEATURES_PATH}")

    logger.info(f"Model v{_meta.get('version')}, {_features} features")


def predict(features: dict) -> float:
    """Predict log revenue from feature vector."""
    if _model is None:
        raise ModelNotReadyError("Model not loaded")
    if _features is None:
        raise ModelNotReadyError("Features not loaded")

    vector = np.array([[features.get(f, 0) for f in _features]])
    log_revenue = _model.predict(vector)[0]
    return float(log_revenue)


def get_model_info() -> dict:
    if _meta is None:
        return {}
    return {
        "model_type": _meta.get("model_type", "unknown"),
        "version": _meta.get("version", "0.0.0"),
        "n_features": len(_features) if _features else 0,
        "metrics": _meta.get("metrics", {}),
    }


def get_feature_columns() -> list[str]:
    return _features or []
