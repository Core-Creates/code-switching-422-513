"""Step 1: the encoder is derived, then verified twice by independent methods.
These are the tests that Sec. 3.3 of the manuscript should have been."""
import functools
import os

import numpy as np
import pytest
import stim

import frames as F
from frames import ps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAIRS = list(zip(F.IN_STAB, F.OUT_STAB)) + [(F.IN_X, F.OUT_X), (F.IN_Z, F.OUT_Z)]


def pauli_matrix(s):
    m = {"I": np.eye(2), "X": np.array([[0, 1], [1, 0]]),
         "Y": np.array([[0, -1j], [1j, 0]]), "Z": np.array([[1, 0], [0, -1]])}
    return functools.reduce(np.kron, [m[c] for c in reversed(s)])


def codeword(stabs, logical_z, eigenvalue=+1):
    P = np.eye(32, dtype=complex)
    for s in stabs:
        P = P @ (np.eye(32) + pauli_matrix(s)) / 2
    P = P @ (np.eye(32) + eigenvalue * pauli_matrix(logical_z)) / 2
    col = max(range(32), key=lambda j: np.linalg.norm(P[:, j]))
    return P[:, col] / np.linalg.norm(P[:, col])


def unitary_from_stim_file(path):
    """Rebuild the unitary in float64 with our own gate matrices. Shares nothing with
    Stim's tableau algebra but the circuit text, so this is an independent check.
    Note: stim's own to_unitary_matrix returns complex64, which shows ~3e-8 leakage
    purely from float32 rounding."""
    H1 = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    S1 = np.array([[1, 0], [0, 1j]], dtype=complex)
    X1 = np.array([[0, 1], [1, 0]], dtype=complex)
    Z1 = np.diag([1, -1]).astype(complex)
    P0 = np.array([[1, 0], [0, 0]], dtype=complex)
    P1 = np.array([[0, 0], [0, 1]], dtype=complex)
    I2 = np.eye(2, dtype=complex)

    def embed(ops):
        return functools.reduce(np.kron, [ops.get(q, I2) for q in reversed(range(5))])

    Um = np.eye(32, dtype=complex)
    for inst in stim.Circuit.from_file(path).flattened():
        t = [x.value for x in inst.targets_copy()]
        if inst.name in ("H", "S", "S_DAG", "X", "Z"):
            g = {"H": H1, "S": S1, "S_DAG": S1.conj().T, "X": X1, "Z": Z1}[inst.name]
            for q in t:
                Um = embed({q: g}) @ Um
        elif inst.name == "CX":
            for c, tg in zip(t[::2], t[1::2]):
                Um = (embed({c: P0}) + embed({c: P1, tg: X1})) @ Um
        elif inst.name == "CZ":
            for c, tg in zip(t[::2], t[1::2]):
                Um = (embed({c: P0}) + embed({c: P1, tg: Z1})) @ Um
        else:
            raise NotImplementedError(inst.name)
    return Um


def test_synthesis_is_reproducible(U):
    """Re-deriving the encoder from the frames must give back encoder.stim."""
    T_in = F.frame_tableau(F.IN_STAB, F.IN_X, F.IN_Z)
    T_out = F.frame_tableau(F.OUT_STAB, F.OUT_X, F.OUT_Z)
    assert T_in.inverse().then(T_out) == U


@pytest.mark.parametrize("src,want", PAIRS)
def test_verification_1_frame_map_with_signs(U, src, want):
    assert U(ps(src)) == ps(want)


@pytest.mark.parametrize("eigenvalue,label", [(+1, "logical 0"), (-1, "logical 1")])
def test_verification_2_statevector(eigenvalue, label):
    Umat = unitary_from_stim_file(os.path.join(ROOT, "encoder.stim"))
    assert np.abs(Umat.conj().T @ Umat - np.eye(32)).max() < 1e-12
    psi_out = Umat @ codeword(F.IN_STAB, F.IN_Z, eigenvalue)
    P_out = np.eye(32, dtype=complex)
    for s in F.OUT_STAB:
        P_out = P_out @ (np.eye(32) + pauli_matrix(s)) / 2
    leakage = 1 - np.linalg.norm(P_out @ psi_out) ** 2
    overlap = abs(np.vdot(codeword(F.OUT_STAB, F.OUT_Z, eigenvalue), psi_out))
    assert leakage < 1e-12, f"{label}: leaks out of the code space"
    assert abs(overlap - 1) < 1e-12, f"{label}: wrong codeword"


def test_exact_resource_counts(encoder_circuit):
    """Banned vocabulary: 'approximately'. These are integers read off the circuit."""
    counts = {}
    for inst in encoder_circuit.flattened():
        n = len(inst.targets_copy())
        counts[inst.name] = counts.get(inst.name, 0) + (n // 2 if inst.name == "CX" else n)
    assert counts == {"H": 12, "S": 15, "CX": 17}


def test_m1_branch_pauli_frame_fix(U):
    """Sec. 3.3 says a Pauli correction 'may' be needed but never says which."""
    fix = None
    for p in F.all_paulis():
        if p.commutes(ps("ZZIII")):
            continue
        if all(p.commutes(ps(s)) for s in F.IN_STAB if s != "ZZIII") \
           and p.commutes(ps(F.IN_X)) and p.commutes(ps(F.IN_Z)):
            p.sign = +1
            fix = p
            break
    assert str(fix).lstrip("+") == "_X___"
    assert str(U(fix)).lstrip("+") == "Y__Y_"
