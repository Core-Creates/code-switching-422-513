"""Step 2: flag placement and decoder synthesis. The fast tests pin the fault model and
the baseline; the exhaustive searches are marked slow (run with: pytest -m slow)."""
import json
import os

import pytest

import flagsearch as FS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_encoder_gate_locations(enc):
    assert enc.n == 44
    assert enc.ncx == 17
    assert enc.arity_histogram == {1: 27, 2: 17}


def test_baseline_fault_counts(enc):
    gate_only = enc.faults(())
    with_idle = enc.faults((), include_idle=True)
    assert len(gate_only) == 337
    assert len(with_idle) == 1010


def test_unflagged_encoder_is_not_fault_tolerant(enc):
    bad, _, ntot, buckets, _ = FS.evaluate(enc.faults(()), False)
    assert len(buckets) == 16
    assert bad == 16, "every bucket mixes logically inequivalent residuals"


def test_collisions_differ_by_a_logical_operator(enc):
    """Same syndrome and same flag, residuals differing by a logical, is exactly what
    makes a bucket undecodable."""
    _, _, _, buckets, badkeys = FS.evaluate(enc.faults(()), False)
    key = badkeys[0]
    reps = {FS.canon(e) for _, e in buckets[key]}
    assert len(reps) > 1
    base = next(iter(reps))
    classes = {FS.logical_class((e[0] ^ base[0], e[1] ^ base[1])) for e in reps}
    assert classes - {"I"}, "residuals must differ by a nontrivial logical"


def test_invalid_flag_designs_are_rejected(enc):
    """A bracketing pair is only a flag if it cancels in the fault-free run and leaves
    the frame map intact. Sec. 4.4's gadget does neither."""
    rejected = 0
    for t2 in range(1, 12):
        if enc.faults((("X", 0, 0, t2),)) is None:
            rejected += 1
    assert rejected > 0, "the validity filter must actually reject something"


def test_flag_readout_flip_is_always_enumerated(enc):
    labels = [f[0] for f in enc.faults((("X", 0, 1, 2),))]
    assert any("readout flip" in l for l in labels)
    assert any("prep flag" in l for l in labels)


def test_sweep_results_are_recorded():
    rows = [json.loads(l) for l in
            open(os.path.join(ROOT, "results", "sweep_rows.jsonl"))]
    assert len(rows) == 24, "all 24 stabilizer bijections were swept"
    assert sum(r["valid_flags"] for r in rows) == 97466
    assert min(r["best_strict"] for r in rows) == 14
    assert not any(r["best_strict"] == 0 for r in rows), \
        "no cascade in the sweep admits a certifying single flag"
    assert min(r["cx"] for r in rows) == 15 and max(r["cx"] for r in rows) == 25


@pytest.mark.slow
def test_exhaustive_single_flag_search_finds_no_certificate(enc):
    nvalid, best_strict, best_postsel = FS.single_flag_search(enc)
    assert nvalid == 3474
    assert best_strict[0] == 16
    assert best_postsel[0] == 15
