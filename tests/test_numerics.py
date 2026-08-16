"""Monte Carlo cross-check on the end-to-end certificate.

The enumeration is combinatorial and the Monte Carlo is statistical. Agreement between
them is worth more than either alone, so the scaling exponent is pinned as a test.
"""
import importlib.util
import json
import math
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        spec.loader.exec_module(mod)
    finally:
        os.chdir(cwd)
    return mod


@pytest.fixture(scope="module")
def saved():
    with open(os.path.join(ROOT, "results", "numerics.json")) as fh:
        return json.load(fh)


def test_certified_protocol_scales_quadratically(saved):
    """No single fault causes an undetectable logical error, so the leading term must be
    quadratic. A slope near 1 would mean the enumeration missed something."""
    assert 1.7 <= saved["certified"]["slope"] <= 2.4


def test_crippled_protocol_scales_linearly(saved):
    """Removing the M1 flag reintroduces a single-fault mechanism, which must show up as
    a linear slope. This is the control that gives the quadratic result meaning."""
    assert 0.8 <= saved["M1 flag removed"]["slope"] <= 1.4


def test_logical_error_stays_below_physical(saved):
    for row in saved["certified"]["rows"]:
        if row["errors"]:
            assert row["p_logical"] < row["p"]


def test_acceptance_rate_is_reported_and_falls_with_p(saved):
    """Post-selection is load-bearing at four stages, so acceptance is a headline number
    and must decrease monotonically in p."""
    accs = [r["acceptance"] for r in saved["certified"]["rows"]]
    assert accs == sorted(accs, reverse=True)
    assert accs[0] > 0.80          # p = 1e-3
    assert accs[-1] < 0.30         # p = 1e-2
    # the simplified protocol nearly doubled the yield at p = 1e-2
    assert accs[-1] > 0.15


def test_exponent_is_quoted_with_an_uncertainty(saved):
    """A slope without an error bar is not a checkable claim."""
    for key in ("certified", "M1 flag removed"):
        assert "slope_sd" in saved[key]
        assert 0 < saved[key]["slope_sd"] < 0.5


def test_the_two_regimes_are_cleanly_separated(saved):
    c, k = saved["certified"], saved["M1 flag removed"]
    sep = abs(c["slope"] - k["slope"]) / (c["slope_sd"] ** 2 + k["slope_sd"] ** 2) ** 0.5
    assert sep > 5, "quadratic and linear scaling must be distinguishable"
