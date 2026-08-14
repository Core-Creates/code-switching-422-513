"""Step 1: synthesize the re-encoding Clifford U by frame composition, then verify it
twice by independent methods (tableau conjugation, raw statevector).

Outputs: encoder.stim, and a printed certificate.
"""
import functools
import numpy as np
import stim

import frames as F
from frames import ps

# ---------------------------------------------------------------- conventions
F.check_frame(F.IN_STAB, F.IN_X, F.IN_Z, "input frame")
F.check_frame(F.OUT_STAB, F.OUT_X, F.OUT_Z, "output frame")

# the [[4,2,2]] logical assignment itself, on 4 qubits
for (xb, zb, other_x, other_z, name) in [
    (F.X1BAR, F.Z1BAR, F.X2BAR, F.Z2BAR, "logical 1"),
    (F.X2BAR, F.Z2BAR, F.X1BAR, F.Z1BAR, "logical 2"),
]:
    assert not ps(xb).commutes(ps(zb)), f"{name}: Xbar/Zbar commute"
    assert ps(xb).commutes(ps(other_x)) and ps(xb).commutes(ps(other_z)), name
    for s in F.S422:
        assert ps(s).commutes(ps(xb)) and ps(s).commutes(ps(zb)), name
print("[ok] conventions self-consistent ([[4,2,2]] logicals, both 5-qubit frames)")

# ------------------------------------------------------------------ synthesis
T_in = F.frame_tableau(F.IN_STAB, F.IN_X, F.IN_Z)
T_out = F.frame_tableau(F.OUT_STAB, F.OUT_X, F.OUT_Z)
U = T_in.inverse().then(T_out)

circuit = U.to_circuit(method="elimination")
circuit.to_file("encoder.stim")

counts = {}
for inst in circuit.flattened():
    n_targets = len(inst.targets_copy())
    gate = inst.name
    per_op = 2 if gate in ("CX", "CY", "CZ", "XCX", "XCZ", "ZCX", "SWAP") else 1
    counts[gate] = counts.get(gate, 0) + n_targets // per_op
two_q = sum(v for k, v in counts.items() if k in ("CX", "CY", "CZ", "XCX", "XCZ", "ZCX", "SWAP"))
one_q = sum(v for k, v in counts.items()) - two_q
print(f"\n[circuit] gates by type: {counts}")
print(f"[circuit] two-qubit gates: {two_q}   single-qubit gates: {one_q}   "
      f"depth: {len(circuit)} instructions (unoptimized)")

# --------------------------------------------- verification 1: tableau algebra
print("\n[verify 1] conjugation of every frame generator, signs included")
pairs = list(zip(F.IN_STAB, F.OUT_STAB)) + [(F.IN_X, F.OUT_X), (F.IN_Z, F.OUT_Z)]
ok = True
U_from_circuit = stim.Tableau.from_circuit(circuit)
assert U_from_circuit == U, "circuit does not reproduce the synthesized tableau"
for src, want in pairs:
    got = U_from_circuit(ps(src))
    good = got == ps(want)
    ok &= good
    print(f"   U {src} U+ = {str(got):8s} want {want:8s} {'OK' if good else 'MISMATCH'}")
assert ok, "frame map failed"

# the m=1 Pauli-frame fix: anticommutes with ZZIII, commutes with everything else
fix = None
for p in F.all_paulis():
    if p.commutes(ps("ZZIII")):
        continue
    if all(p.commutes(ps(s)) for s in F.IN_STAB if s != "ZZIII") \
       and p.commutes(ps(F.IN_X)) and p.commutes(ps(F.IN_Z)):
        p.sign = +1
        fix = p
        break
print(f"\n[frame] m=1 branch is fixed by input Pauli {fix}, "
      f"which U maps to output Pauli {U(fix)}")

# ------------------------------------------ verification 2: raw statevector
def pauli_matrix(s):
    m = {"I": np.eye(2), "X": np.array([[0, 1], [1, 0]]),
         "Y": np.array([[0, -1j], [1j, 0]]), "Z": np.array([[1, 0], [0, -1]])}
    # little-endian: qubit 0 is least significant -> kron from the last char down
    return functools.reduce(np.kron, [m[c] for c in reversed(s)])


def codeword(stabs, logical_z, eigenvalue=+1):
    P = np.eye(2 ** F.N, dtype=complex)
    for s in stabs:
        P = P @ (np.eye(2 ** F.N) + pauli_matrix(s)) / 2
    P = P @ (np.eye(2 ** F.N) + eigenvalue * pauli_matrix(logical_z)) / 2
    col = max(range(2 ** F.N), key=lambda j: np.linalg.norm(P[:, j]))
    v = P[:, col]
    return v / np.linalg.norm(v)


def unitary_from_stim_file(path):
    """Build the 32x32 unitary in float64 from the .stim file using our own gate
    definitions. Independent of stim's tableau algebra: the only shared object is
    the text of the circuit."""
    H1 = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    S1 = np.array([[1, 0], [0, 1j]], dtype=complex)
    X1 = np.array([[0, 1], [1, 0]], dtype=complex)
    P0 = np.array([[1, 0], [0, 0]], dtype=complex)
    P1 = np.array([[0, 0], [0, 1]], dtype=complex)
    I2 = np.eye(2, dtype=complex)

    def embed(ops):  # ops: dict qubit -> 2x2 ; little-endian kron
        return functools.reduce(np.kron, [ops.get(q, I2) for q in reversed(range(F.N))])

    Um = np.eye(2 ** F.N, dtype=complex)
    for inst in stim.Circuit.from_file(path).flattened():
        t = [x.value for x in inst.targets_copy()]
        if inst.name in ("H", "S", "S_DAG", "X", "Z"):
            g = {"H": H1, "S": S1, "S_DAG": S1.conj().T, "X": X1,
                 "Z": np.diag([1, -1]).astype(complex)}[inst.name]
            for q in t:
                Um = embed({q: g}) @ Um
        elif inst.name == "CX":
            for c, tg in zip(t[::2], t[1::2]):
                Um = (embed({c: P0}) + embed({c: P1, tg: X1})) @ Um
        elif inst.name == "CZ":
            for c, tg in zip(t[::2], t[1::2]):
                Um = (embed({c: P0}) + embed({c: P1, tg: np.diag([1, -1]).astype(complex)})) @ Um
        else:
            raise NotImplementedError(inst.name)
    assert np.abs(Um.conj().T @ Um - np.eye(2 ** F.N)).max() < 1e-12
    return Um


Umat = unitary_from_stim_file("encoder.stim")
P_out = np.eye(2 ** F.N, dtype=complex)
for s in F.OUT_STAB:
    P_out = P_out @ (np.eye(2 ** F.N) + pauli_matrix(s)) / 2

print("\n[verify 2] independent statevector check")
for ev, label in [(+1, "logical |0>"), (-1, "logical |1>")]:
    psi_in = codeword(F.IN_STAB, F.IN_Z, ev)
    psi_out = Umat @ psi_in
    want = codeword(F.OUT_STAB, F.OUT_Z, ev)
    leak = 1 - np.linalg.norm(P_out @ psi_out) ** 2
    ovl = abs(np.vdot(want, psi_out))
    print(f"   {label}: leakage out of [[5,1,3]] code space = {leak:.2e}   "
          f"|<target|U|in>| = {ovl:.6f}")
    assert leak < 1e-9 and abs(ovl - 1) < 1e-9

print("\nwrote encoder.stim")
print(circuit)
