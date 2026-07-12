"""Regression test: the API must report the real model version, not a hardcoded one."""
import json

import pytest

from src.config import settings
from src.exceptions import ModelNotReadyError
from src import model as model_mod


def _meta_version():
    with open(settings.META_PATH) as f:
        return json.load(f)["version"]


def test_model_info_version_matches_meta():
    """get_model_info().version (used by /v1/estimate's model_version) == meta.json version.

    Skips gracefully if the native model can't load in this environment
    (e.g. LightGBM shared libs unavailable), so the assertion never gives a
    false failure for an env issue unrelated to the code under test.
    """
    try:
        model_mod.load_model()
    except ModelNotReadyError as e:
        pytest.skip(f"model unavailable in this environment: {e}")

    info = model_mod.get_model_info()
    assert info["version"] == _meta_version()
    # Guard against the old hardcoded-app-version regression.
    assert info["version"] != settings.VERSION or _meta_version() == settings.VERSION
