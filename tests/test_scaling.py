"""The fault enumeration must handle gates of arbitrary arity, not just 1 and 2."""
import os

import pytest
import stim

import flagsearch as FS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_batched_instructions_split_into_one_location_per_gate():
    c = stim.Circuit()
    c.append("I", range(5))
    c.append("H", [1, 2])          # two 1-qubit gates
    c.append("CX", [0, 1, 0, 4])   # two 2-qubit gates
    ops = FS.split_ops(c, nq=5)
    assert len(ops) == 5 + 2 + 2
    assert sorted(o.k for o in ops) == [1] * 7 + [2, 2]


@pytest.mark.parametrize("k", [1, 2, 3, 4, 5])
def test_pauli_count_is_four_to_the_k_minus_one(k):
    assert sum(1 for _ in FS.paulis_on(k)) == 4 ** k - 1


def test_weight_restriction_is_explicit():
    assert sum(1 for _ in FS.paulis_on(3, max_weight=2)) == 3 * 3 + 3 * 9


@pytest.mark.parametrize("name,arity", [("CX", 2), ("H", 1), ("CZ", 2), ("S", 1)])
def test_arity_from_stim_metadata(name, arity):
    assert FS.gate_arity(name) == arity


def test_arity_override_hook_for_gates_stim_lacks():
    assert FS.gate_arity("CCZ", {"CCZ": 3}) == 3
    with pytest.raises(ValueError):
        FS.gate_arity("CCZ")


def test_macro_location_of_arity_three_contributes_63_faults():
    path = os.path.join(ROOT, "encoder.stim")
    enc2 = FS.Encoder(stim.Circuit.from_file(path))
    enc3 = FS.Encoder(stim.Circuit.from_file(path), macros=[(4, 7)])
    big = [op for op in enc3.base if op.label.startswith("MACRO")]
    assert len(big) == 1 and big[0].k == 3
    assert sum(1 for _ in FS.paulis_on(big[0].k)) == 63
    expected = (len(enc2.faults(())) - sum(4 ** op.k - 1 for op in enc2.base[4:7])
                + (4 ** big[0].k - 1))
    assert len(enc3.faults(())) == expected


def test_macro_fusion_preserves_the_unitary():
    path = os.path.join(ROOT, "encoder.stim")
    enc3 = FS.Encoder(stim.Circuit.from_file(path), macros=[(4, 7)])
    tabs, _ = enc3.images(enc3.build(()), 5)
    assert all(tabs[0](stim.PauliString(a)) == stim.PauliString(b) for a, b in FS.PAIRS)


def test_mpp_multi_qubit_measurement_is_one_location():
    c = stim.Circuit()
    c.append("I", range(5))
    c.append("MPP", [stim.target_x(0), stim.target_combiner(), stim.target_z(1),
                     stim.target_combiner(), stim.target_y(2)])
    mpp = [o for o in FS.split_ops(c, nq=5) if o.label.startswith("MPP")]
    assert len(mpp) == 1 and mpp[0].k == 3


def test_fault_model_summary_reports_restrictions(enc):
    full = enc.fault_model_summary()
    restricted = enc.fault_model_summary(max_weight=1)
    assert "restricted" not in full
    assert "restricted" in restricted, "a weight cap must never be silent"
