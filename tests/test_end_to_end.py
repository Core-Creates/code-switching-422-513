"""End-to-end single-fault enumeration over the whole teleportation switch."""
import importlib.util
import os

import pytest
import stim

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def e2e():
    spec = importlib.util.spec_from_file_location("end_to_end",
                                                  os.path.join(ROOT, "end_to_end.py"))
    mod = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        spec.loader.exec_module(mod)
    finally:
        os.chdir(cwd)
    return mod


@pytest.mark.parametrize("basis", ["X", "Z"])
def test_protocol_is_deterministic_without_noise(e2e, basis):
    b = e2e.build(basis, 0.0)
    det, obs = b.c.compile_detector_sampler().sample(1024, separate_observables=True)
    assert det.sum() == 0, "a detector fires with no noise"
    assert obs.sum() == 0, "the teleported observable is wrong"


@pytest.mark.parametrize("basis", ["X", "Z"])
def test_no_undetectable_single_fault_logical_error(e2e, basis):
    assert e2e.scan(e2e.build(basis, 1e-3).c) == 0


def test_positive_control_fails(e2e):
    """The scan must be able to report failure, or a clean result means nothing.
    Removing the M1 flag reintroduces an undetectable single-fault logical error."""
    assert e2e.scan(e2e.build("Z", 1e-3, cripple="m1_flag").c) > 0


def test_composition_gaps_stay_closed(e2e):
    """Regression guards for the three gaps the end-to-end scan exposed, each of which
    was invisible to the per-gadget certificates."""
    src = open(os.path.join(ROOT, "end_to_end.py")).read()
    assert "verify_b(\"final\", noisy=False)" in src, "hand-off EC round on B"
    assert "a_xxxx_m" in src, "A checks interleaved between M1 rounds"
    assert "b_zbar_{r}_flag" in src, "flagged and repeated Zbar frame measurement"
