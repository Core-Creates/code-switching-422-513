"""The teleportation switch: ideal-protocol identity, and fault tolerance of the joint
logical measurement."""
import importlib.util
import os
import sys

import numpy as np
import pytest
import stim

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
def tfa():
    return load("teleport_fault_analysis")


def test_joint_measurement_is_fault_tolerant_with_one_flag(tfa):
    """One flag bracketing the whole 7-CNOT cascade, with post-selection on the flag and
    on the ZZZZ parity of A's destructive readout, leaves every syndrome bucket
    decodable."""
    recs, kept, buckets, bad = tfa.analyze(tfa.DEFAULT_ORDER, (0, 7))
    assert recs is not None, "the flag pair must cancel in the fault-free run"
    assert len(buckets) == 16
    assert bad == [], "undecodable buckets remain"


def test_unflagged_cascade_is_not_fault_tolerant(tfa):
    _, _, _, bad = tfa.analyze(tfa.DEFAULT_ORDER, None)
    assert len(bad) == 9, "without a flag the cascade spreads ancilla errors onto B"


def test_synthesized_decoder_is_the_standard_weight_one_table(tfa):
    """After flagging and post-selection the surviving errors on B are weight one, so the
    synthesized decoder must coincide with the standard [[5,1,3]] lookup. That it does is
    the strongest single check that the gadget behaves."""
    _, _, buckets, bad = tfa.analyze(tfa.DEFAULT_ORDER, (0, 7))
    assert not bad
    for syn, items in buckets.items():
        e = tfa.canon(items[0][1])
        best = min(((e[0] ^ sx, e[1] ^ sz) for sx, sz in tfa.STAB16),
                   key=lambda c: sum(1 for i in range(5)
                                     if (c[0] >> i & 1) or (c[1] >> i & 1)))
        weight = sum(1 for i in range(5) if (best[0] >> i & 1) or (best[1] >> i & 1))
        assert weight <= 1
        assert (syn == (0, 0, 0, 0)) == (weight == 0)


def test_flag_pair_validity_is_enforced(tfa):
    """An unpaired flag CNOT is not a flag. The bracket range must keep both CNOTs."""
    ops = tfa.build(tfa.DEFAULT_ORDER, (0, 7))
    assert sum(1 for _, tg in ops if tg == [tfa.M, tfa.FLAG]) == 2


def test_trivial_faults_are_excluded(tfa):
    """X on the ancilla just after the H is not a fault: the ancilla is in |+> there.
    Y at the same location is the same physical fault as Z."""
    tfa.analyze(tfa.DEFAULT_ORDER, (0, 7))
    assert tfa.analyze.n_trivial > 0
