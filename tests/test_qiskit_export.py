"""The Qiskit translation must be the same protocol, not a second implementation."""
import importlib.util
import io
import contextlib
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
qiskit = pytest.importorskip("qiskit")
pytest.importorskip("qiskit_aer")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
    finally:
        os.chdir(cwd)
    return mod


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, ROOT)
    return load("qiskit_export"), load("end_to_end")


def test_translation_preserves_the_measurement_and_detector_counts(mods):
    Q, E = mods
    circ = E.build("Z", 0.0).c
    qc, detectors, observable = Q.translate(circ, E.NQ)
    assert qc.num_clbits == circ.num_measurements
    assert len(detectors) == circ.num_detectors
    assert observable, "the teleported observable must survive translation"


def test_no_feed_forward_is_required(mods):
    """The Pauli frame is classical bookkeeping, so the exported circuit must contain no
    conditional operations. This is what makes the protocol portable to hardware with
    weak or slow dynamic-circuit support."""
    Q, E = mods
    qc, _, _ = Q.translate(E.build("Z", 0.0).c, E.NQ)
    for inst in qc.data:
        assert getattr(inst.operation, "condition", None) is None
        assert inst.operation.name not in ("if_else", "while_loop", "switch_case")


def test_noiseless_protocol_is_deterministic_in_aer(mods):
    Q, _ = mods
    for basis in ("X", "Z"):
        _, accepted, errors, _ = Q.run(basis, 0.0, 200)
        assert accepted == 200
        assert errors == 0


@pytest.mark.slow
def test_acceptance_agrees_with_stim(mods):
    Q, _ = mods
    import json
    with open(os.path.join(ROOT, "results", "numerics.json")) as fh:
        stim_rows = {r["p"]: r for r in json.load(fh)["certified"]["rows"]}
    shots = 20000
    acc = sum(Q.run(b, 0.005, shots // 2)[1] for b in ("X", "Z")) / shots
    sigma = (0.25 / (shots / 2)) ** 0.5 * 2 ** 0.5
    assert abs(acc - stim_rows[0.005]["acceptance"]) < 4 * sigma
