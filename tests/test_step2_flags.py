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


# ------------------------------------------------------- counting bound (Step 3/4)
def test_flag_bit_lower_bound(enc):
    """Every syndrome class holds 3 or 4 logically inequivalent residuals, so a decoder
    keyed on (syndrome, flag) needs at least 2 flag bits no matter where the couplings
    are placed. This is why every single-flag search fails."""
    for include_idle in (False, True):
        by_syn = {}
        for _, e, _ in enc.faults((), include_idle=include_idle):
            by_syn.setdefault(FS.syndrome(e), set()).add(FS.canon(e))
        sizes = sorted((len(v) for v in by_syn.values()), reverse=True)
        assert len(by_syn) == 16
        assert sizes == [4] * 10 + [3] * 6
        assert (max(sizes) - 1).bit_length() == 2, "at least 2 flag bits are necessary"


def test_widened_family_prefilter_is_selective(enc):
    """The algebraic prefilter is what makes the widened family tractable."""
    keys = FS.coupling_keys(enc, "X")
    assert len(keys) == (enc.n + 1) * 5
    n2 = sum(1 for _ in FS.zero_sum_subsets(keys, 2))
    n3 = sum(1 for _ in FS.zero_sum_subsets(keys, 3, primitive=True))
    assert n2 == 2024 and n3 == 6133


def test_multi_coupling_designs_are_supported(enc):
    """A flag with three couplings on different data qubits is expressible and valid."""
    keys = FS.coupling_keys(enc, "X")
    subset = next(iter(FS.zero_sum_subsets(keys, 3, primitive=True)))
    design = (("X", tuple(subset)),)
    assert FS.normalize(design) == design
    assert FS.normalize((("X", 0, 1, 2),)) == (("X", ((1, 0), (2, 0))),)


@pytest.mark.slow
def test_no_widened_single_flag_certifies(enc):
    stats, results = FS.wide_search(enc, sizes=(2, 3), log=None)
    assert sum(v for _, v in stats.values()) == 17287
    assert not any(r[0] == 0 for r in results)
    assert results[0][0] == 16


def test_size4_flag_family_was_searched_exhaustively():
    """The size-4 cap is gone: the whole primitive space was enumerated, so the
    two-flag negative result cannot be an artifact of sampling."""
    import json
    st = json.load(open(os.path.join(ROOT, "results", "step4_two_flag_summary.json")))
    assert st["candidates"] == 867694
    assert st["distinct_coverages"] == 5384
    assert st["covering_pairs_found"] == 0
    assert st["single_flag_full_cover"] == 0


@pytest.mark.slow
def test_size4_space_size_is_stable(enc):
    """Pins the size of the space so a change in the prefilter cannot silently shrink it."""
    counts = {}
    for kind in ("X", "Z"):
        keys = FS.coupling_keys(enc, kind)
        counts[kind] = sum(1 for _ in FS.zero_sum_subsets(keys, 4, primitive=True))
    assert counts == {"X": 477273, "Z": 372108}
