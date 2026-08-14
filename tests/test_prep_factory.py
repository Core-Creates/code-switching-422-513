"""The |0>_L factory for block B."""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def pf():
    spec = importlib.util.spec_from_file_location("prep_factory",
                                                  os.path.join(ROOT, "prep_factory.py"))
    mod = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        spec.loader.exec_module(mod)
    finally:
        os.chdir(cwd)
    return mod


def test_prep_circuit_is_small_and_correct(pf):
    """Graph-state synthesis beats full-Clifford elimination for a STATE: only the
    Z-images are constrained."""
    assert pf.n2 == 6
    assert pf.method == "graph_state"


def test_no_prep_fault_escapes(pf):
    """Every single fault in preparation is detected by the g1..g4 syndrome, is a
    stabilizer, or is a logical operator absorbed by the recorded frame bit b5. There is
    no fourth case, because B need only be in the code space."""
    assert "?" not in pf.tally
    assert pf.tally["detected"] == 124
    assert pf.tally["I"] == 3
    assert sum(v for k, v in pf.tally.items() if k in ("X", "Y", "Z")) == 3
    assert sum(pf.tally.values()) == 130


def test_verification_cascades_preserve_the_code_space(pf):
    """A fault in a verification cascade either trips the flag, trips the syndrome, or
    leaves the block in the code space."""
    for label, s in pf.summary.items():
        assert s["bad"] == 0, f"{label} lets an error out of the code space"


def test_logical_absorption_requires_zbar_measured_last(pf):
    """The absorption argument is an ORDERING requirement, not a free lunch: b5 must be
    recorded after the syndrome verification, or a logical fault arriving later leaves a
    stale frame bit."""
    assert pf.ZBAR_LAST is True
